from commit_viewer import get_commits_api

url = 'https://github.com/klross/test_repo'
commits = get_commits_api(url)

print(commits)
