import json
import os.path
import pickle
import re
from sys import exit

import requests
from requests.cookies import RequestsCookieJar
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from database import Problem, ProblemTag, Tag, Submission, create_tables, Solution
from utils import destructure, random_wait, do, get
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

COOKIE_PATH = "./cookies.dat"


class LeetCodeCrawler:
    def __init__(self):
        # create an http session
        self.session = requests.Session()
        self.browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )
        self.session.headers.update(
            {
                "Host": "leetcode.com",
                "Cache-Control": "max-age=0",
                "Upgrade-Insecure-Requests": "1",
                "Referer": "https://leetcode.com/accounts/login/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
                "Connection": "keep-alive",
            }
        )

    def login(self):
        browser_cookies = {}
        if os.path.isfile(COOKIE_PATH):
            with open(COOKIE_PATH, "rb") as f:
                browser_cookies = pickle.load(f)
        else:
            print("😎 Starting browser login..., please fill the login form")
            try:
                # browser login
                login_url = "https://leetcode.com/accounts/login"
                self.browser.get(login_url)

                WebDriverWait(self.browser, 24 * 60 * 3600).until(
                    lambda driver: driver.current_url.find("login") < 0
                )
                browser_cookies = self.browser.get_cookies()
                with open(COOKIE_PATH, "wb") as f:
                    pickle.dump(browser_cookies, f)
                print("🎉 Login successfully")

            except Exception as e:
                print(f"🤔 Login Failed: {e}, please try again")
                exit()

        cookies = RequestsCookieJar()
        for item in browser_cookies:
            cookies.set(item["name"], item["value"])

            if item["name"] == "csrftoken":
                self.session.headers.update({"x-csrftoken": item["value"]})

        self.session.cookies.update(cookies)

    def fetch_accepted_problems(self):
        # Get all problems
        response = self.session.get("https://leetcode.com/api/problems/all/")
        all_problems = json.loads(response.content.decode("utf-8"))

        # Get existing problem IDs from database
        existing_problems = {p.id for p in Problem.select(Problem.id)}

        # Filter accepted problems that aren't in database
        counter = 0
        accepted_problems = [
            (item["stat"]["question_id"], item["stat"]["question__title_slug"])
            for item in all_problems["stat_status_pairs"]
            if item["status"] == "ac"
        ]

        # print(accepted_problems, len(accepted_problems))

        # Process new accepted problems
        for problem_id, slug in accepted_problems:
            if problem_id not in existing_problems:
                counter += 1
                # fetch problem
                do(self.fetch_problem, args=[slug, True])
                # fetch solution
                do(self.fetch_solution, args=[slug])

            # always try to update submission
            do(self.fetch_submission, args=[slug])

        print(f"🤖 Updated {counter} problems")

    def fetch_problem(self, slug, accepted=False):
        print(f"🤖 Fetching problem: https://leetcode.com/problem/{slug}/...")
        query_params = {
            "operationName": "getQuestionDetail",
            "variables": {"titleSlug": slug},
            "query": """query getQuestionDetail($titleSlug: String!) {
                        question(titleSlug: $titleSlug) {
                            questionId
                            questionFrontendId
                            questionTitle
                            questionTitleSlug
                            content
                            difficulty
                            stats
                            similarQuestions
                            categoryTitle
                            topicTags {
                            name
                            slug
                        }
                    }
                }""",
        }

        resp = self.session.post(
            "https://leetcode.com/graphql",
            data=json.dumps(query_params).encode("utf8"),
            headers={
                "content-type": "application/json",
            },
        )
        body = json.loads(resp.content)

        # parse data
        question = get(body, "data.question")

        Problem.replace(
            id=question["questionId"],
            display_id=question["questionFrontendId"],
            title=question["questionTitle"],
            level=question["difficulty"],
            slug=slug,
            description=question["content"],
            accepted=accepted,
        ).execute()

        for item in question["topicTags"]:
            if Tag.get_or_none(Tag.slug == item["slug"]) is None:
                Tag.replace(name=item["name"], slug=item["slug"]).execute()

            ProblemTag.replace(
                problem=question["questionId"], tag=item["slug"]
            ).execute()
        random_wait(10, 15)

    def fetch_solution(self, slug):
        print(f"🤖 Fetching solution for problem: {slug}")
        query_params = {
            "operationName": "QuestionNote",
            "variables": {"titleSlug": slug},
            "query": """
            query QuestionNote($titleSlug: String!) {
                question(titleSlug: $titleSlug) {
                    questionId
                    article
                    solution {
                      id
                      content
                      contentTypeId
                      canSeeDetail
                      paidOnly
                      rating {
                        id
                        count
                        average
                        userRating {
                          score
                          __typename
                        }
                        __typename
                      }
                      __typename
                    }
                    __typename
                }
            }
            """,
        }
        resp = self.session.post(
            "https://leetcode.com/graphql",
            data=json.dumps(query_params).encode("utf8"),
            headers={
                "content-type": "application/json",
            },
        )
        body = json.loads(resp.content)

        # parse data
        solution = get(body, "data.question")
        solutionExist = (
            solution["solution"] is not None
            and solution["solution"]["paidOnly"] is False
        )
        if solutionExist:
            Solution.replace(
                problem=solution["questionId"],
                url=f"https://leetcode.com/articles/{slug}/",
                content=solution["solution"]["content"],
            ).execute()
        random_wait(10, 15)

    def fetch_submission(self, slug):
        print(f"🤖 Fetching submission for problem: {slug}")
        try:
            query_params = {
                "operationName": "Submissions",
                "variables": {
                    "offset": 0,
                    "limit": 20,
                    "lastKey": "",
                    "questionSlug": slug,
                },
                "query": """query Submissions($offset: Int!, $limit: Int!, $lastKey: String, $questionSlug: String!) {
                                            submissionList(offset: $offset, limit: $limit, lastKey: $lastKey, questionSlug: $questionSlug) {
                                            lastKey
                                            hasNext
                                            submissions {
                                                id
                                                statusDisplay
                                                lang
                                                runtime
                                                timestamp
                                                url
                                                isPending
                                                __typename
                                            }
                                            __typename
                                        }
                                    }""",
            }
            resp = self.session.post(
                "https://leetcode.com/graphql",
                data=json.dumps(query_params).encode("utf8"),
                headers={
                    "content-type": "application/json",
                },
            )
            body = json.loads(resp.content)

            # Add debug print
            # print(f"Response body: {body}")

            submissions = get(body, "data.submissionList.submissions")
            if not submissions:
                print(f"No submissions found for {slug}")
                return

            for sub in submissions:
                if Submission.get_or_none(Submission.id == sub["id"]) is not None:
                    continue

                if sub["statusDisplay"] == "Accepted":
                    url = sub["url"]
                    full_url = f"https://leetcode.com{url}"
                    # print(f"Fetching submission from: {full_url}")

                    # Add longer wait time
                    self.browser.get(full_url)
                    try:
                        #  adjust timeout as needed
                        element = WebDriverWait(self.browser, 10).until(
                            EC.presence_of_element_located((By.ID, "result_date"))
                        )

                        # Add debug print of page source if element is found
                        html = self.browser.page_source
                        # print(f"Found result_date element, page length: {len(html)}")

                        pattern = re.compile(
                            r"submissionCode: \'(?P<code>.*)\',\n  editCodeUrl", re.S
                        )
                        matched = pattern.search(html)

                        if not matched:
                            print("Could not find submission code pattern in page")
                            print(
                                f"Page source: {html[:1000]}..."
                            )  # Print first 1000 chars
                            continue

                        code = matched.groupdict().get("code")
                        if code:
                            Submission.insert(
                                id=sub["id"],
                                slug=slug,
                                language=sub["lang"],
                                created=sub["timestamp"],
                                source=code.encode("utf-8"),
                            ).execute()
                            # print(f"Successfully saved submission {sub['id']}")
                        else:
                            print(
                                f"No code found in match groups: {matched.groupdict()}"
                            )

                    except Exception as e:
                        print(f"Error processing submission {sub['id']}: {str(e)}")
                        continue

        except Exception as e:
            print(f"Error fetching submissions for {slug}: {str(e)}")

        random_wait(10, 15)


if __name__ == "__main__":
    create_tables()
    crawler = LeetCodeCrawler()
    crawler.login()
    crawler.fetch_accepted_problems()
