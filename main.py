import requests
import json
import random
import xmltodict
import sys
import os
import tomllib

class CLIVars:
    plextoken = "MY_PLEX_TOKEN"
    plexhost = "https://plex.example.com"
    machineid = "1234"

    playlistid = "12345"
    playlistSearch = "episode.unwatched%3D1%26and%3D1%26show.country%3D679"
    playlistName = "CanadaPlaylist.json"
    playlistItemLimit = 20
    trimOnly = False
    verbose = False

def getMachineIdentifier(plexhost, plextoken):
    machineResult = requests.get("{}/identity/?X-Plex-Token={}".format(plexhost, plextoken))
    plexDict = xmltodict.parse(machineResult.text)
    return plexDict

def stringToFile(fileName, contentsRaw):
    contents = str(contentsRaw)
    with open(fileName, "w+") as output_file:
        output_file.write(contents)
        output_file.close()

def fileToString(fileName) :
    fileContents = ""
    with open(fileName, 'r') as myfile:
        fileContents = myfile.read()
    return str(fileContents)

def getCandidateTVShows(plexhost, plextoken, playlistSearch):
    episodeList = requests.get("{}/library/sections/2/all?X-Plex-Token={}&{}".format(plexhost, plextoken, playlistSearch))
    plexDict = xmltodict.parse(episodeList.text)
    return plexDict

def getCurrentPlaylist(plexhost, plextoken, playlistid):
    playlistStatus = requests.get("{}/playlists/{}/items?X-Plex-Token={}".format(plexhost,  playlistid, plextoken))
    plexDict = xmltodict.parse(playlistStatus.text)
    return plexDict

def removeFromPlaylist(plexhost, plextoken, playlistid, playlistitem):
    deleteResult = requests.delete("{}/playlists/{}/items/{}?X-Plex-Token={}".format(plexhost, playlistid, playlistitem, plextoken))
    plexDict = xmltodict.parse(deleteResult.text)
    return plexDict

def getUnwatchedEpisodeFromShow(plexhost, plextoken, showid):
    seasonResult = requests.get("{}/library/metadata/{}/children?X-Plex-Token={}&episode.unwatched=1".format(plexhost, showid, plextoken))
    seasonDict = xmltodict.parse(seasonResult.text)
    seasonId = "none"
    if type([]) == type(seasonDict["MediaContainer"]["Directory"]):
        seasonFound = 99999
        for season in seasonDict["MediaContainer"]["Directory"]:
            if season["@title"] != "All episodes":
                if int(season["@index"]) < seasonFound:
                    seasonFound = int(season["@index"])
                    seasonId = season["@ratingKey"]
    else:
        season = seasonDict["MediaContainer"]["Directory"]
        seasonId = season["@ratingKey"]
    episodeResult = requests.get("{}/library/metadata/{}/children?X-Plex-Token={}&episode.unwatched=1".format(plexhost, seasonId, plextoken))
    plexDict = xmltodict.parse(episodeResult.text)
    return plexDict

def addItemToPlaylist(plexhost, plextoken, playlistid, machineid, libraryid, verbose):
    plexURL = "{}/playlists/{}/items?X-Plex-Token={}&uri=server://{}/com.plexapp.plugins.library{}".format(plexhost, playlistid, plextoken, machineid, libraryid)
    addItemResult = requests.put(plexURL)
    plexDict = xmltodict.parse(addItemResult.text)
    plexDict["url"] = plexURL
    if verbose:
        print("Added item {} to playlist.".format(libraryid))
    return plexDict

def updatePlaylistFromFilter(plexhost, plextoken, playlistid, playlistName, machineid, playlistSearch, targetNumberOfEpisodes, trimOnly, verbose):
    # Step One, remove watched Episodes from list
    oldPlaylist = getCurrentPlaylist(plexhost, plextoken, playlistid)
    stringToFile(playlistName, json.dumps(oldPlaylist, indent=4))
    if type([]) == type(oldPlaylist["MediaContainer"]["Video"]):
        for episode in oldPlaylist["MediaContainer"]["Video"]:
            if "@viewCount" in episode.keys():
                if int(episode["@viewCount"]) > 0:
                    removal = removeFromPlaylist(plexhost, plextoken, playlistid, episode["@playlistItemID"])
    else:
        # if the playlist has only one item then MediaContainer.Video isn't a list, it's a dictionary. Weird, but that's probably an artifiact of my xmltodict stuff.
        episode = oldPlaylist["MediaContainer"]["Video"]
        if "@viewCount" in episode.keys():
            if int(episode["@viewCount"]) > 0:
                removal = removeFromPlaylist(plexhost, plextoken, playlistid, episode["@playlistItemID"])
    if trimOnly:
        print("Not adding any shows, just removing.")
        return
    showsPresent = []
    showsToAddOptions = []
    newPlaylist = getCurrentPlaylist(plexhost, plextoken, playlistid)
    if type([]) == type(newPlaylist["MediaContainer"]["Video"]):
        for episode in newPlaylist["MediaContainer"]["Video"]:
            showsPresent.append(episode["@grandparentTitle"])
    else:
        episode = newPlaylist["MediaContainer"]["Video"]
        showsPresent.append(episode["@grandparentTitle"])

    if len(showsPresent) < targetNumberOfEpisodes:
        print("Only {} episodes in {}. Adding more".format(len(showsPresent), playlistName))    
        showCandidates = getCandidateTVShows(plexhost, plextoken, playlistSearch)
        showOptionsTitles = []
        for show in showCandidates["MediaContainer"]["Directory"]:
            if show["@title"] not in showsPresent:
                showsToAddOptions.append(show)
                showOptionsTitles.append(show["@title"])
        if verbose:
            print("Show options: {}".format(showOptionsTitles))
        stringToFile("showsToAdd.json", json.dumps(showsToAddOptions))
        addCount = targetNumberOfEpisodes - len(showsPresent)
        if len(showsToAddOptions) > addCount:
            showsToAdd = random.sample(showsToAddOptions, addCount)
        else:
            showsToAdd = showsToAddOptions
        showsAdded = []
        print("Taking {} random shows from pool of {}.".format(len(showsToAdd), len(showsToAddOptions)))
        for show in showsToAdd:
            unwatchedEpisodes = getUnwatchedEpisodeFromShow(plexhost, plextoken, show["@ratingKey"])
            if verbose:
                fileName = "unwatched Episodes {}.json".format(show["@title"])
                stringToFile(fileName, json.dumps(unwatchedEpisodes))
            episodeFound = 99999
            libraryid = "none"
            # This should be a list of unwatched episodes
            if type([]) == type(unwatchedEpisodes["MediaContainer"]["Video"]):
                for episode in unwatchedEpisodes["MediaContainer"]["Video"]:
                    if int(episode["@index"]) < episodeFound and episode["@parentTitle"] != "Specials":
                        episodeFound = int(episode["@index"])
                        libraryid = episode["@key"]
                        if verbose:
                            print("Candidate Episode {} {} E{}".format(episode["@grandparentTitle"], episode["@parentTitle"], episode["@index"]))
            # When there's only one episode left, it's not a list that's returned but a dictionary
            elif type({}) == type(unwatchedEpisodes["MediaContainer"]["Video"]):
                episode = unwatchedEpisodes["MediaContainer"]["Video"]
                episodeFound = episode["@index"]
                libraryid = episode["@key"]
                if verbose:
                    print("Candidate Episode {} {} E{}".format(episode["@grandparentTitle"], episode["@parentTitle"], episode["@index"]))
            # If this object is neither a list nor a dictionary then I don't know what it is. Maybe there's an API change.
            else:
                if verbose:
                    print("unwatchedEpisodes[\"MediaContainer\"][\"Video\"] is a {}".format(type(unwatchedEpisodes["MediaContainer"]["Video"])))
            if libraryid != "none":
                if verbose:
                    print("New {} episode being added.".format(show["@title"]))
                addResult = addItemToPlaylist(plexhost, plextoken, playlistid, machineid, libraryid, verbose)
                #stringToFile("addResult-{}.json".format(libraryid.replace("/", ".")), json.dumps(addResult))
                showsAdded.append(show["@title"])
            else:
                if verbose:
                    print("{} was chosen and had {} candidate episodes but none matched.".format(show["@title"], len(unwatchedEpisodes["MediaContainer"]["Video"])))
        showsAddedString = ""
        i = 0
        for show in showsAdded:
            if i == len(showsAdded) - 1 and i != 0:
                showsAddedString = "{}, and {}".format(showsAddedString, show)
            elif i !=0:
                showsAddedString = "{}, {}".format(showsAddedString, show)
            elif i == 0:
                showsAddedString = show
            i = i + 1
        print("Added new episodes to {} from {}.".format(playlistName, showsAddedString))
    else:
        print("Already {} shows in {}. No need for more.".format(len(showsPresent), playlistName))


# Define some variables
verbose = False
if "-v" in sys.argv:
    verbose = True

trimOnly = False
if "-trim" in sys.argv:
    trimOnly = True

# Load playlists
currentPath = os.path.realpath(__file__).replace("main.py", "")
playlistFileString = fileToString("{}playlists.toml".format(currentPath))
playlists = tomllib.loads(playlistFileString)

# Load config
confstring = fileToString("{}conf.toml".format(currentPath))
conf = tomllib.loads(confstring)["variables"]

plextoken = conf["plex-token"]
plexhost = conf["plex-host"]
targetNumberOfEpisodes = conf["targetNumberOfEpisodes"]
machineid = getMachineIdentifier(plexhost, plextoken)["MediaContainer"]["@machineIdentifier"]

for k in playlists.keys():
    playlist = playlists[k]
    updatePlaylistFromFilter(plexhost=plexhost, plextoken=plextoken, playlistid=playlist["playlistid"], playlistName=playlist["name"], machineid=machineid, playlistSearch=playlist["playlistSearch"], targetNumberOfEpisodes=targetNumberOfEpisodes, trimOnly=trimOnly, verbose=verbose)