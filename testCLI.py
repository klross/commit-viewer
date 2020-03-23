from commit_viewer import get_commits_cli, check_url

url = 'https://github.com/klross/test_repo'
commits = get_commits_cli(url, persist = False)
print(commits)
