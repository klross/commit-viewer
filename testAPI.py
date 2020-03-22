from commit_viewer import get_commits_api, clean_commits_api

url = 'https://github.com/klross/test_repo'
commits = get_commits_api(url)
clean_commits = clean_commits_api(commits)
print(clean_commits)
