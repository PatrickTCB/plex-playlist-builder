import requests
import sys
import json
import random
import xmltodict
import os
import tomllib
import time
from datetime import datetime
from zoneinfo import ZoneInfo

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

def getUnwatchedEpisodeFromPlaylist(plexhost, plextoken, playlistID, existingPlaylistItems):
    playlistEpisode = 0
    playlistResult = requests.get("{}/playlists/{}/items?X-Plex-Token={}".format(plexhost, playlistID, plextoken))
    plexDict = xmltodict.parse(playlistResult.text)
    for episode in plexDict["MediaContainer"]["Video"]:
        if "@viewCount" in episode.keys():
            if int(episode["@viewCount"]) == 0:
                if episode["@key"] not in existingPlaylistItems:
                    return episode["@key"]
                else:
                    # This means the next unwatched episode from this playlist is already in the playlist
                    return 0
        else:
            if episode["@key"] not in existingPlaylistItems:
                return episode["@key"]
            else:
                # This means the next unwatched episode from this playlist is already in the playlist
                return 0
    return playlistEpisode

def addItemToPlaylist(plexhost, plextoken, playlistid, machineid, libraryid, verbose):
    plexURL = "{}/playlists/{}/items?X-Plex-Token={}&uri=server://{}/com.plexapp.plugins.library{}".format(plexhost, playlistid, plextoken, machineid, libraryid)
    addItemResult = requests.put(plexURL)
    plexDict = xmltodict.parse(addItemResult.text)
    plexDict["url"] = plexURL
    return plexDict

def updatePlaylistFromFilter(plexhost, plextoken, playlistid, playlistName, playlistShows, machineid, playlistSearch, spokenOutputName, spokenOutput, targetNumberOfEpisodes, trimOnly, verbose, dryRun):
    if verbose:
        print("Geting old version of {}".format(playlistName))
    # Step One, remove watched Episodes from list
    oldPlaylist = getCurrentPlaylist(plexhost, plextoken, playlistid)
    existingPlaylistItems = []
    if verbose:
        stringToFile("old-{}".format(playlistName), json.dumps(oldPlaylist, indent=4))
    if "Video" in oldPlaylist["MediaContainer"].keys():
        if type([]) == type(oldPlaylist["MediaContainer"]["Video"]):
            for episode in oldPlaylist["MediaContainer"]["Video"]:
                if "@viewCount" in episode.keys():
                    if int(episode["@viewCount"]) > 0:
                        if dryRun:
                            print("Dry Run. Not removing {} from {}.".format(episode["@playlistItemID"], playlistid))
                        else:
                            removeFromPlaylist(plexhost, plextoken, playlistid, episode["@playlistItemID"])
                else:
                    existingPlaylistItems.append(episode["@key"])
        else:
            # if the playlist has only one item then MediaContainer.Video isn't a list, it's a dictionary. Weird, but that's probably an artifiact of my xmltodict stuff.
            episode = oldPlaylist["MediaContainer"]["Video"]
            if "@viewCount" in episode.keys():
                if int(episode["@viewCount"]) > 0:
                    if dryRun:
                        print("Dry Run. Not removing {} from {}.".format(episode["@playlistItemID"], playlistid))
                    else:
                        removeFromPlaylist(plexhost, plextoken, playlistid, episode["@playlistItemID"])
                else:
                    existingPlaylistItems.append(episode["@key"])
            else:
                existingPlaylistItems.append(episode["@key"])
    else:
        if verbose:
            print("No old episodes to remove from {}. It seems empty.".format(playlistName))
    if trimOnly:
        print("Not adding any shows, just removing.")
        return
    showsPresent = []
    showsToAddOptions = []
    newPlaylist = getCurrentPlaylist(plexhost, plextoken, playlistid)
    if verbose:
        stringToFile("mostrecentlist.json", json.dumps(newPlaylist))
    if "Video" in newPlaylist["MediaContainer"].keys():
        if type([]) == type(newPlaylist["MediaContainer"]["Video"]):
            for episode in newPlaylist["MediaContainer"]["Video"]:
                showsPresent.append(episode["@grandparentTitle"])
        else:
            episode = newPlaylist["MediaContainer"]["Video"]
            showsPresent.append(episode["@grandparentTitle"])
    else:
        if verbose:
            print("{} seems empty so the showsPresent list is also empty".format(playlistName))

    if len(showsPresent) < targetNumberOfEpisodes:
        if spokenOutput == False:
            print("Only {} episodes in {}. Adding more".format(len(showsPresent), spokenOutputName))    
        showCandidates = getCandidateTVShows(plexhost, plextoken, playlistSearch)
        showOptionsTitles = []
        for show in showCandidates["MediaContainer"]["Directory"]:
            if show["@title"] not in showsPresent:
                showsToAddOptions.append(show)
                showOptionsTitles.append(show["@title"])
        if verbose:
            print("Show options: {}".format(showOptionsTitles))
            stringToFile("showsToAdd.json", json.dumps(showsToAddOptions))
        playlistShowsAdded = 0
        if targetNumberOfEpisodes - len(showsPresent) > 0:
            for playlistShow in playlistShows:
                unwatchedEpisode = getUnwatchedEpisodeFromPlaylist(plexhost, plextoken, playlistShow, existingPlaylistItems)
                if unwatchedEpisode != 0:
                    playlistShowsAdded = playlistShowsAdded + 1
                    if dryRun:
                        print("Was going to add {} from playlistid {}".format(unwatchedEpisode, playlistShow))
                    else:
                        addItemToPlaylist(plexhost, plextoken, playlistid, machineid, unwatchedEpisode, verbose)
        addCount = targetNumberOfEpisodes - len(showsPresent) - playlistShowsAdded
        if len(showsToAddOptions) > addCount:
            showsToAdd = random.sample(showsToAddOptions, addCount)
        else:
            showsToAdd = showsToAddOptions
        showsAdded = []
        if spokenOutput == False:
            print("Taking {} random shows from pool of {} shows and {} playlists.".format(len(showsToAdd), len(showsToAddOptions), len(playlistShows)))
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
                if dryRun:
                    print("Would have added episode {} to playlist {}".format(libraryid, playlistid))
                else:
                    addItemToPlaylist(plexhost, plextoken, playlistid, machineid, libraryid, verbose)
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
        if len(showsToAdd) > 0:
            print("Added new episodes to {} from {}.".format(spokenOutputName, showsAddedString))
        else:
            print("No new shows can be added to {}.".format(spokenOutputName))
            if verbose:
                print("While the number of episodes in {} is {} and the target number of episodes was {}. There were only {} canditate shows. Therefore no episodes could be added to playlist.".format(spokenOutputName, len(showsPresent), targetNumberOfEpisodes, len(showCandidates["MediaContainer"]["Directory"])))
    else:
        print("Already {} shows in {}. No need for more.".format(len(showsPresent), spokenOutputName))

# Define some variables
spokenOutput = False
if "-spokenOutput" in sys.argv:
    spokenOutput = True

verbose = False
if "-v" in sys.argv:
    verbose = True

trimOnly = False
if "-trim" in sys.argv:
    trimOnly = True

dryRun = False
if "-dryRun" in sys.argv:
    dryRun = True

if spokenOutput == False:
    if "RUNHOUR" in os.environ:
        print("Script started. Will update playlists at {}h".format(os.environ["RUNHOUR"]))
    else:
        print("Script started. No RUNHOUR set, so the playlists will just updated now one time.")

loop = True
while loop:
    now = datetime.now(ZoneInfo(os.environ["TIMEZONE"]))
    todayDate = now.strftime("%Y-%m-%d %H:%M:%S")
    thisHour = now.strftime("%H")
    if "RUNHOUR" in os.environ:
        runHour = os.environ["RUNHOUR"]
    else:
        runHour = thisHour
    if spokenOutput:
        runHour = thisHour
    if str(runHour) == str(thisHour):
        if spokenOutput == False:
            print("Starting: {}".format(todayDate))
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
            # playlistShows are playlists that the tool will pretend are shows.
            if "playlistShows" not in playlist.keys():
                playlist["playlistShows"] = []
            if spokenOutput == False:
                print("Updating {}".format(playlist["spokenOutputName"]))
            updatePlaylistFromFilter(plexhost=plexhost, plextoken=plextoken, playlistid=playlist["playlistid"], playlistName=playlist["name"], playlistShows=playlist["playlistShows"], machineid=machineid, playlistSearch=playlist["playlistSearch"], spokenOutputName=playlist["spokenOutputName"], spokenOutput=spokenOutput, targetNumberOfEpisodes=targetNumberOfEpisodes, trimOnly=trimOnly, verbose=verbose, dryRun=dryRun)
    if spokenOutput:
        loop = False
    elif "RUNHOUR" not in os.environ:
        loop = False
    else:
        time.sleep(3600)
    
