import requests
import json
import random
import xmltodict

def getMachineIdentifier(plexhost, plextoken):
    machineResult = requests.get("{}/identity/?X-Plex-Token={}".format(plexhost, plextoken))
    plexDict = xmltodict.parse(machineResult.text)
    return plexDict

def stringToFile(fileName, contentsRaw):
    contents = str(contentsRaw)
    with open(fileName, "w+") as output_file:
        output_file.write(contents)
        output_file.close()

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

def addItemToPlaylist(plexhost, plextoken, playlistid, machineid, libraryid):
    plexURL = "{}/playlists/{}/items?X-Plex-Token={}&uri=server://{}/com.plexapp.plugins.library{}".format(plexhost, playlistid, plextoken, machineid, libraryid)
    addItemResult = requests.put(plexURL)
    plexDict = xmltodict.parse(addItemResult.text)
    plexDict["url"] = plexURL
    return plexDict

def updatePlaylistFromFilter(plexhost, plextoken, playlistid, playlistName, machineid, playlistSearch, playlistItemLimit):
    # Step One, remove watched Episodes from list
    oldPlaylist = getCurrentPlaylist(plexhost, plextoken, playlistid)
    stringToFile(playlistName, json.dumps(oldPlaylist, indent=4))
    if type([]) == type(oldPlaylist["MediaContainer"]["Video"]):
        for episode in oldPlaylist["MediaContainer"]["Video"]:
            if "@viewCount" in episode.keys():
                if int(episode["@viewCount"]) > 0:
                    removeFromPlaylist(plexhost, plextoken, playlistid, episode["@playlistItemID"])
    else:
        # if the playlist has only one item then MediaContainer.Video isn't a list, it's a dictionary. Weird, but that's probably an artifiact of my xmltodict stuff.
        episode = oldPlaylist["MediaContainer"]["Video"]
        if "@viewCount" in episode.keys():
            if int(episode["@viewCount"]) > 0:
                removeFromPlaylist(plexhost, plextoken, playlistid, episode["@playlistItemID"])

    showsPresent = []
    showsToAddOptions = []
    newPlaylist = getCurrentPlaylist(plexhost, plextoken, playlistid)
    if type([]) == type(newPlaylist["MediaContainer"]["Video"]):
        for episode in newPlaylist["MediaContainer"]["Video"]:
            showsPresent.append(episode["@grandparentTitle"])
    else:
        episode = newPlaylist["MediaContainer"]["Video"]
        showsPresent.append(episode["@grandparentTitle"])

    if len(showsPresent) < playlistItemLimit:
        print("Only {} episodes in {}. Adding more".format(len(showsPresent), playlistid))    
        showCandidates = getCandidateTVShows(plexhost, plextoken, playlistSearch)
        for show in showCandidates["MediaContainer"]["Directory"]:
            if show["@title"] not in showsPresent:
                showsToAddOptions.append(show)
        addCount = playlistItemLimit - len(showsPresent)
        showsToAdd = random.sample(showsToAddOptions, addCount)
        showsAdded = []
        print("Taking {} random shows from pool of {}.".format(len(showsToAdd), len(showsToAddOptions)))
        for show in showsToAdd:
            unwatchedEpisodes = getUnwatchedEpisodeFromShow(plexhost, plextoken, show["@ratingKey"])
            episodeFound = 99999
            libraryid = "none"
            if type([]) == type(unwatchedEpisodes["MediaContainer"]["Video"]):
                for episode in unwatchedEpisodes["MediaContainer"]["Video"]:
                    if int(episode["@index"]) < episodeFound and episode["@parentTitle"] != "Specials":
                        episodeFound = int(episode["@index"])
                        libraryid = episode["@key"]
            if libraryid != "none":
                addItemToPlaylist(plexhost, plextoken, playlistid, machineid, libraryid)
                showsAdded.append(show["@title"])
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
        print("Added new episodes to {} from {}.".format(playlistid, showsAddedString))
    else:
        print("Already {} shows in {}. No need for more.".format(len(showsPresent), playlistid))

# Define some variables
plextoken = "MY_PLEX_TOKEN" # https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
plexhost = "https://plex.example.com"
machineid = getMachineIdentifier(plexhost, plextoken)["MediaContainer"]["@machineIdentifier"]

# Example Dynamic Playlist
# This gets untached shows from Canada
# You could have as many instances of this block as there are playlists you want to update.
playlistid = "12345" # This you can pull from a the playlist URL.
playlistSearch = "episode.unwatched%3D1%26and%3D1%26show.country%3D679"
playlistName = "DynamicPlaylist.json"
playlistItemLimit = 20

updatePlaylistFromFilter(plexhost, plextoken, playlistid, playlistName, machineid, playlistSearch, playlistItemLimit)