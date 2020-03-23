import json
import requests
import subprocess
from subprocess import Popen, PIPE
import os
import django
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import sys



#function to get commits through GitHub command line
def get_commits_cli(url, persist = False):

    #check valid URL
    check_url(url)
    
    #ask user where they would like to clone repository (or path to existing directory)
    path = input("Enter path for new or existing directory: ")
    
    #only clone if directory does not already exist
    command = ['if cd {}; then git pull; else git clone {} {}; fi'.format(path, url, path)]
    command_run = subprocess.call(command, shell = True)

    #assert successful clone
    assert os.path.isdir(path)

    #acces new directory
    os.chdir(path)

    
    if persist == True:
        try: #check if you need to retrieve full commit history or only new commits, then retrieve
            lines = check_tag()
        except: #if above command fails resort to retrieving entire commit history
            lines = subprocess.check_output(['git', 'log','--pretty=format:%H - %an - %ae - %ad - %s'], stderr=subprocess.STDOUT)

    #if data is not being persisted retrieve entire commit history    
    else:
        try:
            lines = subprocess.check_output(['git', 'log','--pretty=format:%H - %an - %ae - %ad - %s'], stderr=subprocess.STDOUT)
        except: #would only fail if empty repository
            print('The repository is empty. No commits.')
            lines = b''
        
    #parse commits
    lines = (lines.decode()).split('\n')
    commits = []
    current_commit = {}
    
    for line in lines:
        line = line.split(' - ')
        
        try:
            assert len(line) == 5
            current_commit['hash'] = line[0]
            current_commit['author'] = line[1]
            current_commit['email'] = line[2]
            current_commit['date'] = line[3]
            current_commit['message'] = line[4]
            
        except ValueError:
            pass
        
        except AssertionError:
            pass
        
        commits.append(current_commit)
        current_commit = {}

    assert len(commits) == len(lines)
    
    return commits



#function to get full commits through GitHub API - unnecessary data will be cleaned later
def get_commits_api(url):
    
    #check url, extract owner and repository names
    repo, owner = check_url(url)
    
    try:
        commits = []
        next = True
        i = 1
        while next == True:

            gh_session = requests.Session()
            url = 'https://api.github.com/repos/{}/{}/commits?page={}&per_page=100'.format(owner, repo, i)
            commit_pg = gh_session.get(url = url)
            commit_pg_list = [dict(item, **{'repo_name':'{}'.format(repo)}) for item in commit_pg.json()]    
            commit_pg_list = [dict(item, **{'owner':'{}'.format(owner)}) for item in commit_pg_list]
            commits = commits + commit_pg_list
            if 'Link' in commit_pg.headers:
                if 'rel="next"' not in commit_pg.headers['Link']:
                    next = False
            i = i + 1
            
    except ValueError:
        
        commit_pg = gh_session.get(url = url).json()
        
        if commit_pg["message"] == "Git Repository is empty.":
            print('The repository is empty. No commits.')
            commits = []
            
        elif commit_pg["message"] == "Not Found":
            print("The page was not found with provided URL")
            
        else:
            print("Authentification may be required: unable to access private repositories \
or repositories with too many commits (requests limited to 60 an hour for unauthenticated users)")

    return commits


#only keep useful data from get_commits_api
def clean_commits_api(commits):

    clean_commits = []
    current_commit = {}
    for commit in commits:
        try:
            current_commit['hash']  = commit['sha']
            current_commit['author'] = commit['commit']['committer']['name']
            current_commit['email'] = commit['commit']['committer']['email']
            current_commit['date'] = commit['commit']['committer']['date']
            current_commit['message'] = commit['commit']['message']
        except ValueError:
            pass
        clean_commits.append(current_commit)
        current_commit = {}
    return json.dumps(clean_commits)



#check url validity
def check_url(url):
    val = URLValidator()
    try:
        val(url)
        repo = url.rsplit('/', 1)[-1]
        owner = url.rsplit('/', 2)[-2]
        return repo,owner
    except ValidationError:
        redo = input('Invalid URL, type again or e to exit: ')
        if redo == 'e':
            sys.exit(1)
        else:
            check_url(redo)


         
#GENERALIZATION: test api retrieval first, fallback on cli retrieval
def run_app():
    url = input("Enter GitHub URL: ")  

    #try with GitHub API  
    try:
        print('API retrieval')
        commits = get_commits_api(url)
        commits = clean_commits_api(commits)
        return commits
    
    #fallback onto CLI implemtation if above fails, and persist
    except:
        print('CLI retrieval')
        commits = get_commits_cli(url, persist = False)
        return commits




#PERSIST DATA

#functions to create and delete tags
def create_tag():
    new_tag = subprocess.check_output(['git', 'tag', 'persisted_commits'], stderr=subprocess.STDOUT)
    return new_tag

def delete_tag():
    delete = subprocess.check_output(['git', 'tag', '-d','persisted_commits'], stderr=subprocess.STDOUT)
    return delete


#function to read json file
def read_json(filename = 'commit_list.json'):
    with open(filename) as file:
        data = json.load(file)
    return data


        
#function to check if json file exists
def where_json(filename = 'commit_list.json'):
    return os.path.exists(filename)


#main functionto persist data, will rely on get_commits_cli
#TODO - incorporate persist data into get_commits_cli (under persist = true arg)
def persist_data(url, filename = 'commit_list.json'):
    data = get_commits_cli(url, persist = True)
    #check if file exists and create it if doesn't exist
    if where_json():
        update_json(data, filename)
        try: #need to update tag to latest commit
            delete_tag() 
            create_tag()
        except: #handle case of empty repository, no tag to delete
            commits = [{}]
            
    else:
        with open(filename, 'w') as outfile:  
            json.dump(data, outfile)
        try:
            create_tag() #next time you will only persist newest commits
        except: #handle case of empty repository, can't create tag
            commits = [{}]

    commits = read_json(filename)
    return commits



#update commit file if it already exists
def update_json(new_commits, filename = 'commit_list.json'):
    commits = read_json(filename)
    #no update if no new commits
    if new_commits == [{}]:
        new_commits = commits    
    else:
        new_commits.extend(commits)
        #is there a way to do this w\o overwriting the file?
        with open(filename, 'w') as outfile:  
            json.dump(new_commits, outfile)       
    return new_commits


#if 'persisted_commits' tag exists only retrieve commits since tag
#otherwise retrieve all commits
def check_tag():
    
    check = subprocess.check_output(['git', 'tag', '-l', 'persisted_commits'], stderr=subprocess.STDOUT)
    if check == b'persisted_commits\n':
        lines = subprocess.check_output(['git', 'log', 'persisted_commits..HEAD', '--pretty=format:%H - %an - %ae - %ad - %s'], stderr=subprocess.STDOUT)
    else:
        try: 
            lines = subprocess.check_output(['git', 'log','--pretty=format:%H - %an - %ae - %ad - %s'], stderr=subprocess.STDOUT)
        except: #empty repository case
            lines = b'' 
    return lines




