import requests
import json

#in this file all Wikipedia API requests needed to create the excel file of statement development are listed

#input: pageid, unique id of the Wikipedia article for which the request is done
#output: json file containing unique revision ids from max. 500 revisons, which can be used to get information
#        about earlier versions of the article
def get_rv_ids(pageid):
    #see also: https://www.mediawiki.org/w/api.php?action=help&modules=query%2Brevisions
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"
    PARAMS = {
        "action": "query",
        "prop": "revisions",
        "pageids": str(pageid),
        "rvlimit": "max",  #"2", #"max", (number of revisons, max means 500)
        "rvprop": "ids|timestamp", #information to get (here revisionid and time of the revision)
        "rvdir": "newer", #sorted from old to new
        "format": "json"
    }
    return S.get(url=URL, params=PARAMS).json()


#input: pageid, unique id of the Wikipedia article for which the request is done
#       cont, continue command (this is a command one gets back if there are more revisons than specified in 'rvlimit'),
#             which basically gives a start/continue point for this request
#output: json file containing unique revision ids from max. 500 revisons, which can be used to get information
#        about earlier versions of the article (starting at the continue command point)
def get_rv_ids_cont(pageid, cont):
    #more details see above (get_rv_ids) and https://www.mediawiki.org/w/api.php?action=help&modules=query%2Brevisions
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"
    PARAMS = {
        "action": "query",
        "prop": "revisions",
        "pageids": str(pageid),
        "rvlimit": "max",
        "rvprop": "ids|timestamp",
        "rvcontinue": str(cont),
        "rvdir": "newer",
        "format": "json"
    }
    return S.get(url=URL, params=PARAMS).json()


#input: rvid, unique id of the revision (of Wikipedia article) for which the request is done
#output: json file containing the complete html text of the given revision
def get_text_from_rv(rvid):
    #see also https://www.mediawiki.org/w/api.php?action=help&modules=parse
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"
    PARAMS = {
        "action": "parse", #note that in this case the parse command is needed instead of the query command for the
                           #current version of an article
        "prop": "text",
        "oldid": str(rvid),
        "format": "json"
    }
    return S.get(url=URL, params=PARAMS).json()


#input: pageid, unique id of the Wikipedia article for which the request is done
#output: json file containing the basic information (like title, language, ...) for the given article
def get_info(pageid):
    #see also: https://www.mediawiki.org/w/api.php?action=help&modules=query%2Binfo
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"
    PARAMS = {
        "action": "query",
        "prop": "info",
        "pageids": str(pageid),
        "format": "json"
    }
    return S.get(url=URL, params=PARAMS).json()

#this module can be used to test the single requests. Therefore the hashtag in front of the
#non tab-intended test_everything command at the end of the function need to be deleted, afterwards run the script.
#However in non-test cases (especially if this file is imported) the test_everything() must be commented out.
def test_everything():
    pageid = 72671 #Angela Merkel
    pageid = 28176
    rvcontinue = "20060623095637|60147540"
    rvid = 363371475#358 #172695940
    test_get_rv_id = get_rv_ids(pageid)
    test_get_rv_ids_cont = get_rv_ids_cont(pageid, rvcontinue)
    test_get_text_from_rv_id = get_text_from_rv(rvid)
    test_get_info = get_info(pageid)
    #print(json.dumps(test_get_rv_id, indent=4, sort_keys=True))
    print(json.dumps(test_get_rv_ids_cont, indent=4, sort_keys=True))
    #print(json.dumps(test_get_text_from_rv_id, indent=4, sort_keys=True))
    #print(json.dumps(test_get_info, indent=4, sort_keys=True))
test_everything()