# Plex Playlist Updater

Plex has a lot of smart playlist options, but what I wanted was a playlist built out of the next unwatched epsiode from some selection of TV shows.

That's what this script does. 

# Setup
## Conf.toml
Create your own config file

`cp conf-example.toml conf.toml`

Then replace the placeholder values with your real Plex token and Plex host info. Plex Tokens [are retrieved in the browser](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

## Playlists.toml
Create your own playlist file

`cp playlist-example.toml playlist.toml`

Then edit yours so that the playlist IDs are correct. Once your playlist is created in Plex simply navigate to it in a web browser and get the playlist ID from the `playlists` value in the URL.

The variable `playlistSearch` takes search filters which you can get from going to "Advanced Filters" in the search.

The part you'd need to take out form the `playlistSearch` variable is going to be something like `show.network%3D90469`. In this specific case it filters for shows by CBC Television, though the specific network ID is not guaranteed to be the same on your system.

### Playlist Shows

Some shows (like Buffy & Angel) need to be watched in a specific order. In order to accomodate this, you can create a playlist with the show(s) episodes in what you feel is the correct order and then add the playlist id to a variable called `playlistShows` in your `playlist.toml`. See the example file for how this should look.

The next unwatched episode from this playlist show will be added to the playlist as if it were any other TV show.

# Usage
Once you've got everything setup run the script

`python3 main.py`

For verbose output

`python3 mainy.py -v`

To just trim playlists of watched episodes without adding new ones

`python3 main.py -trim`

I run this script via a cron job on my Plex server. But it can be run anywhere that can access your Plex server.

If you're using a voice assistant (like Siri) which can run commands like this, you can optimize the output to be spoken using the flag `-spokenOutput`.

`python3 main.py -spokenOutput`