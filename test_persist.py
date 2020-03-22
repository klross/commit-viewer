import subprocess
from commit_viewer import persist_data

#a first run through this will persist the data
url = 'https://github.com/klross/test_repo'
commits = persist_data(url, filename = 'commit_list.json')
print(commits)


#lets commit the newly created commit list and update our commit data

command_add = ['git', 'add', 'commit_list.json']
git_add = subprocess.check_output(command_add, stderr=subprocess.STDOUT)
command_commit = ['git', 'commit', '-m', 'new_commit']
git_commit = subprocess.check_output(command_commit, stderr=subprocess.STDOUT)

updated_commits = commits = persist_data(url, filename = 'commit_list.json')
print(commits)
