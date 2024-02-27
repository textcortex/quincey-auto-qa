import json
import requests
import os


GITHUB_TOKEN = ""
OPENAI_API_KEY = ""
DISCORD_WEBHOOK_URL = ""
GITHUB_REPO = 'org/repo'  # Replace with your repo name


def create_github_issue(title, body):
    url = 'https://api.github.com/repos/textcortex/report-issues/issues'
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {GITHUB_TOKEN}'
    }
    data = {'title': title, 'body': body}
    response = requests.post(url, headers=headers, json=data)
    if response.ok:
        return response.json()['html_url']
    else:
        raise Exception(f"GitHub Issue could not be created: {response.content}")


def send_discord_message(title, issue_url, report_url, comment, color):
    # depending on the report type, we will send a different message
    data = {
          "content": None,
          "embeds": [
            {
              "title": title,
               "description": f"**Issue Link**: [GitHub Issue]({issue_url})\n**yBug Report**: "
                              f"[View Report]({report_url})\n\n**Excerpt**: {comment[:200]}...",
               "color": color
            }
          ]
        }
    headers = {"Content-Type": "application/json"}
    response = requests.post(DISCORD_WEBHOOK_URL, headers=headers, json=data)
    if response.status_code != 204:
        raise Exception(f"Discord message could not be sent: {response.content}")


def generate_issue(bug_report, key):
    """
    Send prompt to OpenAI API and get the completion
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}"}
    data = {
        "model": "gpt-4-1106-preview",
        "messages": [
            {
                "role": "system",
                "content": 'Your name is Quincey, and you are the Senior QA Engineer at TextCortex. Your task is to read the contents of a given user bug report'
                           'and then write a concise but detailed GitHub issue description that will be used by the developers to fix the bug. The bugs being reported'
                           'can be coming from web application interface of textcortex which is a ai chat platform that takes user input and gives them a response.'
                           'Users can also upload their knowledge bases and files to ask questions to. Remember to keep the issue description absolutely concise but not lacking any important details. Your issue description must absolutely have action points that starts with the -[ ] markdown syntax. Do NOT put more then 3 action points.'
                           'Your response will ONLY consist of the following JSON output: {"title": "gh_issue_title", "body": "gh_issue_body"}'
                           '\n\nREMEMBER: Your response must be valid JSON and NOTHING ELSE.'
            },
            {
                "role": "user",
                "content": f"Here is the user's bug report to analyse:\n\n{bug_report}",
            },
            {
                "role": "assistant",
                'content': '{"title":'
                
            }
        ],
        "temperature": 0.6,
        "max_tokens": 2048,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        out = response.json().get("choices")[0].get("message").get("content")
        # Parse the output to make sure output is valid JSON
        print(out)
        return json.loads(out, strict=False)
    else:
        response.raise_for_status()


def process_ybug_webhook(data):
    comment = data['comment']
    try:
        report_type = data['type']['name']
    except Exception:
        report_type = "Feedback"
    # Green for non-bug reports, red for bug reports.
    color = 0x00FF00 if report_type != "Bug" else 0xFF0000

    # Prompt for OpenAI's GPT service.
    if report_type == "Bug":
        json_resp = generate_issue(comment, OPENAI_API_KEY)
        title = json_resp['title']
        body = json_resp['body']
        # Creating a GitHub Issue using GitHub fine-grained token.
        issue_url = create_github_issue(title, body)

    else:
        title = "New Feedback Report: " + data['title']
        # use the ybug_hook data to sent the contents of the report to Discord
        issue_url = data['reportUrl']
        body = data['comment']
        color = 0x00FF00
        # Don't create a github issue for feedback reports

    # Sending a message to Discord with crucial information for developers
    send_discord_message(title, issue_url, data['reportUrl'], comment, color)
    res = generate_issue(body, OPENAI_API_KEY)
    gh_issue_title = res['title']
    gh_issue_body = f"- Ybug Report URL: {data['reportUrl']}\n\n" + res['body']
    create_github_issue(gh_issue_title, gh_issue_body)
    print("Generated GitHub Issue and sent Discord message successfully.")
    return


def handler(pd: "pipedream"):
    process_ybug_webhook(pd.steps["trigger"]["event"]["body"])
    # Return data for use in future steps
    return
