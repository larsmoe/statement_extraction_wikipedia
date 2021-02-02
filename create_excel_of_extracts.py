from lxml import html #needed to work with the html files of the revisions
import lxml #needed to catch the lxml.etree.ParserError
import requests #needed to catch internet connection problems
import os #needed to create paths of the excel files
import numpy as np #needed in the test_everything to create np arrays
from wiki_API_requests import get_rv_ids, get_rv_ids_cont, get_text_from_rv, get_info #needed for the API requests
import time #needed to wait ten seconds in the case of internet connection problems
from bs4 import BeautifulSoup #needed to find the header of each revision
from pandas import DataFrame #needed to create a DataFrame for each article
import pandas as pd #needed to save the DataFrame to an excel
import xlsxwriter #needed to catch errors with forbidden excel sheet names
import json #needed in the case of debugging to print the answers of the API requests

#for use in other files import the function create_statement_development (see comments there)
#WARNING: IF THERE EXCEL FILES IN THE SAME DICTIONARY AS THIS FILE NAMED Wikipedia_article_statement_no_1.xlsx,
#Wikipedia_article_statement_no_2.xlsx, THEY WILL BE OVERWRITTEN BY THIS SCRIPT. RUN SCRIPT ONLY IF YOU SAVED
#THIS FILES AT ANOTHER LOCATION

CUR_DIR = os.path.dirname(os.path.realpath(__file__)) #dictionary, where this file is saved

#input: pageid_arr - array of pageids, for which a statement development should be done
#       sheets_per_workbook - statement development is saved in an excel file, where each page gets
#           an own sheet. This parameter sets the maximal number of sheets per excel file. If the number
#           exceeds the number of pages, multiple excel files will be created, by default 200
#       show_progress - boolean, if True the progress of most timely part of the process, the download of
#           the html pages of all versions of all pages, is printed to the console
#output: None, instead it is saved in excel file(s)
def create_statement_development(pageid_arr, sheets_per_workbook=200, show_progress=True):
#function first creates a dictionary of all revision ids, which is used to create an dictionary
#of all different article introductions, which is then saved in an excel or multiple excels if the number
#of pageids exceeds sheets_per_workbook. In each sheet of the excel file(s) the development of the first
#section (the introduction) of one Wikipedia article is given. The sheet is named like the article, except if
#the text contains characters, which are forbidden in excel sheets names (like "\") or is too long (31 characters).
#In this case the sheet is named like the pageid
#for detailed description see the single functions
    print('total number of articles: ' + str(len(pageid_arr)))
    dict_of_rev, total_number_of_rev = create_dict_of_rv_ids(arr_pageids=pageid_arr)
    print('total number of revisions: ' +str(total_number_of_rev))
    dict_of_intros = create_dict_of_extracts(dict_of_rev, total_number_of_rev, show_progress)
    create_excel(dict_of_intros, sheets_per_workbook)


#input: arr_pageid: array of pageids
#output: dict_of_rev: dictionary of all revision ids for the pages from the pageid array
#        total_number_of_rev: total number of all revisions in all articles (for information purposes)
def create_dict_of_rv_ids(arr_pageids):
    total_number_of_rev = 0 #counts the total number of revisions (for information purposes only)
    dict_of_rev = {} #this will be returned in the end
    for pageid in arr_pageids: #iterate over all pages
        dict_of_single_page_rev = {} #array where all revision ids for a single pageid will be saved
        cont_exist = True #the API of Wikipedia has a limit of 500 revisions per request, however
                          #if more revisions exists, there is a continue command sent back.
                          #For every request we will check if such a command exists and as long as there is
                          #the while loop will run

        cont = False      #if the request is a continue request, we need a another syntax in the request
                          #we get back from the Wikipedia Server, so this parameter will become true if it is
                          #a continue request

        while cont_exist:
            pageid = int(pageid) #pageid need to be an integer for a correct answer from the Wikipedia API
            internet_connection = False #to avoid a failure when a internet disconnect occurs
            while not internet_connection:
                try:
                    if cont: #if it is a continue request we need two parameters
                        request_json = get_rv_ids_cont(pageid, rvcont)
                    else: #the first request only needs one parameter
                        request_json = get_rv_ids(pageid)
                    internet_connection = True #if the request was succesful the while loop will be left
                except requests.ConnectionError: #if there is no internet a warning is printed and the program will
                                                 #wait for ten seconds before trying again to send a request
                    print('Bad internet connection')
                    time.sleep(10)
            #print(json.dumps(request_json))
            try:
                for revision in request_json["query"]["pages"][str(pageid)]["revisions"]:
                #example of an the answer from an normal API request of the page with pageid 9984491
                #{'continue':{'continue': "||", 'rvcontinue': '20200912144539|203608019'},
                #{'query':{'pages':{'9984491'#(pageid):{'ns':0, 'pageid':9984491, 'revision':
                #[{'parentid': 9984491, 'revid': 167526629, 'timestamp': "2017-07-23T20:03:51Z"},
                #{'parentid': 167526629, 'revid': 167585246, 'timestamp': "2017-07-25T17:58:03Z"}, ...
                #... (all revisions) ]}}}}}
                #the rvcontinue from the first line is the continue command, which is used to get more revisions
                #note that the revisions come from old to new

                    revid = revision["revid"] #with the revison id one can get the text and other information from older
                                              #versions of a page
                    revtime = revision["timestamp"] #date and time of the revison (format see above)
                    dict_of_single_page_rev[revid] = revtime #revison id is saved together with the time in the dictionary
                                                             #described above
                try: #check if there is a continue command (if there wouldn't be any further revisions this command would be
                     #missing and therefore raise a KeyError
                    rvcont = request_json["continue"]["rvcontinue"] #see in the example
                    cont = True #since it is now a continue command we need to use another request (see after the first try above)
                except KeyError:
                    cont_exist = False #leave the while loop
            except KeyError:
                print(json.dumps(request_json, indent=4, sort_keys=True))
                cont_exist = False
        total_number_of_rev += len(dict_of_single_page_rev.keys())
        dict_of_rev[pageid] = dict_of_single_page_rev #this is a dictionary of dictonaries
    return dict_of_rev, total_number_of_rev


#input: dict_of_rev: the dictionary of revsions craeted in the function create_dict_of_rv_ids above
#       total_number_of_rev: total number of revisions and therefore of API requests (for printing
#       information of the progress of the program only)
#output: dict_of_intro: dictionary of all the different introductions (first few senctences) for all
#        pages from the pageid list
def create_dict_of_extracts(dict_of_rev, total_number_of_rev, progress_info=True):
    i = 0 #count for the number of API requests
    one_percents = 0 #count of the progress of the function
    dict_of_intros = {} #this dictionary will be returned at the end
    pageids = dict_of_rev.keys()
    for pageid in pageids: #iterate over all pageids
        cur_text = "" #in this string the current introduction will be saved to compare at which point there are changes
        header = "" #in some cases the function will not find a haeder in early versions of Wikipedia articles (reason
                    #described below around line 150). To avoid that in this case the last header of the former article
                    #is used the header variable is set back to an empty string
        dict_of_diff_intro = {} #in this dictionary all the different introductions for a single page will be saved
        revids = dict_of_rev[pageid].keys() #dict_of_rev is a dictionary of dictionaries (as described in the function
                                            #create_dict_of_rv_ids, and the keys in the inner dictionary are the
                                            #revision ids
        for revid in revids:
            i += 1 #each revision of a arbitrary article results in a increment
            if progress_info:
                if i/total_number_of_rev >= one_percents + 0.01: #track the progress in one percent steps and print it on
                    one_percents = int(np.floor(i/total_number_of_rev)) #the console ogether with the current article the function
                    title_request_json = get_info(pageid)        #works with. A detailed description is below of this request
                    title = title_request_json["query"]["pages"][str(pageid)]["title"] #is given in the funtion create_excel
                    print('progress in revision requests: ' + str(int(one_percents*100)) +\
                          '%, currently working on article: ' +str(title))
            internet_connection = False #to avoid problems in the case of internet disconnetions (see create_dict_of_rv_ids)
            while not internet_connection:
                try:
                    request_json = get_text_from_rv(revid) #this request returns the complete text from the given revison
                                                           #in html format
                    internet_connection = True
                except requests.ConnectionError:
                    print('Bad internet connection')
                    time.sleep(10)
            #an example of a such answer of an API request looks like this:
            #{'parse': {'pageid': 145, 'revid':358', 'text':{'*': "<div class=\"mw-parser-output\"><div class=\"hintergrundfarbe1 [...]
            #<p><b>Angela Dorothea Merkel</b> (* <a href=\"/wiki/17._Juli\" title=\"17. Juli\">17. Juli</a> <a href=\"/wiki/1954\" [...]
            #}, 'title': 'Angela Merkel' } }
            #since this is not very helpful there needs to be some work to bring this in a readable way
            raw_html = request_json["parse"]["text"]["*"] #get the html code of the page
            soup = BeautifulSoup(raw_html, 'lxml') #make the html code to a soup object to make it easier to search
            potential_header = soup.find_all("p") #the header always is part of a html p-pag (<p> ... <\p>)
                                                  #this line finds all p-tags and save them in a list
            for pot_head in potential_header:
                #this for loop searches for the header. Therefore it uses the fact that a Wikipedia article always starts
                #with a sentences containing the title of the article (or something close to the title) and that this
                #title always is printed bold (and that the title is the first word (and most of time the only) part
                #of the article, which is printed bold
                if pot_head.find_all("b") == []: #this command find all html b tags (<b> ... <\b>, b for bold)
                                                 #and lists them, if the list is empty the p-tag contains no bold
                                                 #part (and is therefore not the introduction)
                    continue
                else:   #however if the it contains a bold part it is the header (as explained above)
                    header = pot_head
            header_html = str(header) #change the soup object back to normal html
            try: #this try is to catch cases, where no header was found in the version. This happens especially with very
                 #early versions of articles, where the title was not printed in bold. In this case the plain_text
                 #is set to an empty string, which normally leads to the revison being skipped, since the cur_text
                 #is set to be an empty string at beginning for each pageid
                working_version = html.document_fromstring(header_html)  #create a html document (like a html object)
                try: #in this step it can happen that if the article was deleted at one point a IndexError occurs
                     #if that is the case the revision will be skiped
                    working_version2 = working_version.xpath('//p')[0] #creating an xpath object (see Wikipedia: xpath)
                except IndexError:
                    continue
                plain_text = working_version2.text_content()  # deleting all html tags
            except lxml.etree.ParserError:
                plain_text = ""

            if plain_text == cur_text: #check if the the introduction has changed
                continue #if not skip this revision
            else:
                timestamp = dict_of_rev[pageid][revid] #if it changed save the time and
                timestamp = str(timestamp).replace('T', ' ').replace('Z', '')
                dict_of_diff_intro[timestamp] = plain_text #the new introduction.
                cur_text = plain_text #Furthermore update the current introduction variable
        dict_of_intros[pageid] = dict_of_diff_intro #after iterating over all pageids append the
                                                    #dictionary of all introductions to the dictionary of all
    return dict_of_intros                           #pageids (dictionary of dictionaries) and return it


#input: dict_of_header, the dictionary of dictionaries from the function create_dict_of_extracts above,
#                       containing all the different introductions for all pageids
#       sheets_per_excel, each article (pageid) is saved in a single excel sheet and this number is the
#                         maximum number of sheets per file. if the number of pages exceeds this number
#                         multiple excel files will be created (by default 200)
#Output: None, instead excel file(s) in the folder, where this file is saved will be created
def create_excel(dict_of_header, sheets_per_excel=200):
    #print(dict_of_header)
    pageids = dict_of_header.keys() #get all pageids
    workbook_count = 1 #this count will go up every sheet_per_excel steps (counts how many excel files will be created)
    sheet_count = 1 #this count will go up after every pageid and counts how many pages there are
    for pageid in pageids: #iterate over all pageids
        timestamp = dict_of_header[pageid].keys() #create a list of all times when a the introduction of the given pageid was cahnged
        intro = dict_of_header[pageid].values() #create a list of all introductions. Note that now each index of both
                                                #list belongs together (time[5] is the time the introduction was
                                                #changed to intro[5])
        #create a two-dimensional list (list-command) where described as above time[5] is zipped with intro[5]
        #and then creating a Dataframe from this list with the column titles 'time' and 'introduction'
        df = DataFrame(list(zip(timestamp, intro)), columns=['time', 'introduction'])

        if sheet_count == 1:
            # creating the path for the excel, where the dataframe will be saved (CUR_DIR is the path to the folder,
            # where this file is saved. The name of the excel file contains a variable part (workbook_count), so that
            # after sheets_per_excel pageids a new file is used
            excel_path = os.path.join(CUR_DIR, 'Wikipedia_article_statement_no_' + str(workbook_count) + '.xlsx')
            writer = pd.ExcelWriter(excel_path, engine='xlsxwriter')  # create a ExcelWriter Object to the path created above
        internet_connection = False
        while not internet_connection: #catch internet connection errors, detailed explanation see create_dict_of_rv_ids
            try:
                title_request_json = get_info(pageid) #request basic information (especially the title) of the current article
                internet_connection = True
            except requests.ConnectionError:
                print('no internet connection')
                time.sleep(10)

        #example of an answer of such a info request (pageid:9984491):
        #{batchcomplete:"", 'query':{'pages':{'9984491':{'contentmodel':'wikitext', lastrevid:167585246, 'length': 3235,
        # 'ns': 0, 'pageid': 9984491, 'pagelanguage': 'de', 'pagelanguagedir': 'ltr', pagelanguagehtmlcode': 'de',
        #'title': 'Olympische Winterspiele 1932/Teilnehmer (Norwegen)', 'touched': '2020-08-11T03:09:46Z'}}}
        title = title_request_json["query"]["pages"][str(pageid)]["title"] #get the title of the page
        try: #to avoid errors especially from backslashes in titles, which are not allowed in excel sheet titles
            df.to_excel(writer, sheet_name=str(title)) #write the dataframe to the excel from above in a sheet with the
                                                       #title of the page as name
        except (ValueError, xlsxwriter.exceptions.InvalidWorksheetName) as e: #in case of a forbidden char just take the pageid as title
            df.to_excel(writer, sheet_name=str(pageid))
        if sheet_count % sheets_per_excel == 0: #if the pageid count modulo sheets_per_excel is 0, the current
            writer.save() #excel file contain sheets_per_excel sheets and therefore a new file is needed. Therefore
            workbook_count += 1 #first save the "full" excel than increase the workbook count and create a new excel file
            excel_path = os.path.join(CUR_DIR, 'Wikipedia_article_statement_no_' + str(workbook_count) + '.xlsx')
            writer = pd.ExcelWriter(excel_path, engine='xlsxwriter')
        sheet_count += 1  # increasing the pageid count
    writer.save() #save the last excel file, which is not full at this point (if sheets_per_excel divides the number of
                  #pageids without remainder then the last excel file will be saved empty



#test file for debugging
def test_everything():
    test_ids = np.zeros(2) #array with test ids, where articles are saved with a small amount of revisions so that the
                           #runtime is relatively fast (1-4) and two cases(5-6), which I already did by hand to check
                           #check for correctness. Just choose the length of the test_id array and remove the hashtags
                           #in front of the needed ids
    #test_ids[2] = 334920 #Unterreichenbach
    test_ids[0] = 43819759 #Olympische Winterspiele 1932/Teilnehmer (Norwegen)
    test_ids[1] = 1574572876543566 #Jenisberg
    #test_ids[3] = 5407056 #Thomas Rosch
    #test_ids[4] = 26386 #Willis Tower
    #test_ids[5] = 1576026 #Julius Brink
    create_statement_development(test_ids, 4, False)
    #dict_of_rv = create_dict_of_rv_ids(test_ids)       #for test
    #dict_of_text = create_dict_of_extracts(dict_of_rv) #of the single functions
    #dict_test = {9984491: {'2017-07-23 20:03:51': 'Männer\n'}, 986543: {'2017-07-23 20:03:51': 'Männer\n'}, \
    #                334920:{'2017-07-23 20:03:51': 'Männer\n'}, 5407056:{'2017-07-23 20:03:51': 'Männer\n'}}
    #dictionary to test last function
    #create_excel(dict_test, 3)

#in a test scenario remove hashtag in all other cases comment this line out:
test_everything()