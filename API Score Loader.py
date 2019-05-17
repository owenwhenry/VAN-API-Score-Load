# -*- coding: utf-8 -*-
"""
Created on Thu Sep 13 14:56:25 2018

@author: owen.henry

Function of this script is to connect to the EveryAction 8 API and load a score
using the filejobs API

Key pieces are connecting to the API, sending the file
"""

import requests
import os
import time
from api_key import demo_api_key, prod_api_key, ftp_dest_url, ftp_url
import ftp_info
import pandas as pd
import zipfile
from ftplib import FTP
import json

ftp = FTP(ftp_url)
auth_list = ('crs.scores.api', prod_api_key + '|1') 

def main():
    file_to_send = find_file()
    zipped_file = zip_it(file_to_send)
    api_test()
    scoreid = select_score()
    ftp_ship_it(zipped_file)
    fileloadingjob(zipped_file, file_to_send, ftp_url, scoreid)
    #fileloadingjob('score_file.zip', 'test_score.csv', ftp_dest_url, 25237)
    #ftp_test()
    #score_approve(50562)

#Step 1: Ask where the file lives, get its path, get its name, and check
#what is in the file to make sure it's the correct one

def find_file():
    file_found = 'N'

    while file_found != 'Y':
        """
        file_path = input("Enter file path:")
        
        os.chdir(file_path)
        print(os.getcwd())
"""        
        file_name = input("Enter file name:")
        
        #Make sure you get the file name right
        while os.path.isfile(file_name) != True:
            print('Error: File does not exist')
            print('')
            time.sleep(1)
            file_name = input('Enter file name:')
        
        created = os.path.getctime(file_name)
        last_mod = os.path.getmtime(file_name)
        
        print('File found.')
        
        print('')
        time.sleep(1)
        
        print('File was created at ' + time.strftime("%a, %d %b %Y %H:%M:%S",
                                                     time.localtime(created)))
        print('')
        time.sleep(1)
        print('File was last modified at ' + time.strftime("%a, %d %b %Y %H:%M:%S",
                                                     time.localtime(last_mod)))
        print('')
        time.sleep(1)
        
        data = pd.read_csv(file_name, sep=',', 
                         encoding = 'utf-8-sig', engine = 'python')
        df = pd.DataFrame(data)
        
        print("Here's a summary of what's in the file:")
        print('')
        
        print(df.count())
        
        time.sleep(1)
        
        print('Is this the file you wanted?')
        
        time.sleep(1)
        
        file_found = input('Type Y to continue, N to restart:')
        print('')

    time.sleep(1)
    
    print("Excellent, let's load a score!")

    return(file_name)

#step 2: zip the file
def zip_it(file):
    file_name = input('Please enter the name for the file:')
    if os.path.exists(file_name):
        os.remove(file_name)
    with zipfile.ZipFile(file_name, mode='w') as thezip:
        thezip.write(file)
    
    return file_name

#step 3: put it on the ftp
def ftp_ship_it(file):
    ftp.login(ftp_info.user, ftp_info.passwrd)
    print(ftp.getwelcome())
    ftp.dir()
    with open(file, mode='rb') as send_file:
        ftp.storbinary('STOR ' + file, send_file)
    ftp.quit()

#step 4: get the list of available scores from the API
def select_score():
    url = 'https://api.securevan.com/v4/scores'
    request = requests.get(url, auth = auth_list)
    print(request.text)
    
    score = input('From the above scores, which ScoreID are you updating?')
    
    return score

#step 4: engage with the EA API    
def fileloadingjob(zipped_file, file, sourceurl, scoreid):
    #This function requires a lot of user-entered params
    #Idea here is that there's very specific information that needs to get
    #into the API call, according to the documentation available at
    #https://developers.everyaction.com/van-api#file-loading-jobs
    url = 'https://api.securevan.com/v4/fileloadingjobs'
    #Need a better method for defining what the columns to be used in the file
    #are, rather than user entry - should be able to select from the initial
    #array, as presented by Pandas
    #Also need a better method for building the file name into the request
    #also source url?
    #file_params = "{\n\"columnDelimiter\": \"csv\", \"columns\":, \"filename\":,\"hasheader\": true, \"sourceurl\"}"
    
    #step 4.1: get the columns in the file
    columns = get_columns(file)
    
    print('These are the columns in the file:')
    print(columns)
    #Step 4.2: set the file parameters
    full_url = ftp_dest_url + zipped_file
    file_params = {'filename': file, 'hasheader': 'True', 'sourceurl' : full_url,
                    'columndelimiter': 'csv', 'columns' : columns}
    #Step 4.3: set the actions
    personidcolumn = input('Please specify the column with the ID:')
    
    scorecolumn = input('Please specify the column with the score:')
    
    description = input('Please enter a description for the score:')
    
    actions_params = [ {'actionType' : 'score', 'personIdColumn' : personidcolumn,
                      'personIdType': 'VANID', 'scoreId' : scoreid, 
                      'scoreColumn' : scorecolumn} ]
    
    listener_params = {"type": "EMAIL", "value" : 'owen.henry@crs.org'}
    
    payload = {'description': description, 'file': file_params, 
               'actions' : actions_params, 'listeners' : listener_params}
    headers = {
            'content-type': "application/json",
            'cache-control': "no-cache"
            } 
    
    
    print(json.dumps(payload))
    
    send_file = requests.post(url, auth = auth_list, json = payload, headers = headers)
    print(send_file.text)

def pretty_print_POST(req):
    """
    borrowed from Stack Overflow author AntonioHerraizS
    """
    print('{}\n{}\n{}\n\n{}'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        req.body,
    ))
    
#Small function to return the columns in a file as an array/dict    
def get_columns(file):
    data = pd.read_csv(file, sep=',', 
                         encoding = 'utf-8-sig', engine = 'python')
    df = pd.DataFrame(data)
    
    columns = []
    rowval = 0
    for header in df:
        print(header)
        #columns['col'+ str(rowval)] = header
        #rowval += 1
        columns.append({"name": header})
    return(columns)

#quick function that tests if the API key given is working and some other info
def api_test():
    url = "https://api.securevan.com/v4/echoes"
    payload = "{\n\"message\": \"Hello, world\"\n}"
    headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",

            }
    
    response = requests.request("POST", url, auth = auth_list, data=payload, headers=headers)
    pretty_print_POST(response.request)
    print(response.request)
    print(response.url)
    print(response.text)
    
    print("Great, we're connected to the API!")

def ftp_test():
    ftp.login(ftp_info.user, ftp_info.passwrd)
    print(ftp.getwelcome())
    ftp.dir()
    #with open(file, mode='rb') as send_file:
    #    ftp.storbinary('STOR ' + file, send_file)
    ftp.quit()
    
def score_approve(ScoreUpdateID):
    url = 'https://api.securevan.com/v4/ScoreUpdates/' + str(ScoreUpdateID)
    
    headers = {
            'content-type': "application/json",
            'cache-control': "no-cache"
            } 
    payload = {'loadStatus' : 'Approved'}
    
    send_file = requests.patch(url, auth = auth_list, json = payload, headers = headers)
    print(send_file.text)

def view_scores():
    url = 'https://api.securevan.com/v4/scoreUpdates'
    
    headers = {
            'content-type': "application/json",
            'cache-control': "no-cache"
            } 
    #payload = {'loadStatus' : 'Approved'}
    
    send_file = requests.get(url, auth = auth_list, headers = headers)
    
    
    print(send_file.text) 

score_approve(53918)
score_approve(53917)
view_scores()