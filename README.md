# Plex Playlist Updater

Plex has a lot of smart playlist options, but what I wanted was a playlist built out of the next unwatched epsiode from some selection of TV shows.

That's exactly what this script does. The variable `playlistSearch` takes search filters which you can get from going to "Advanced Filters" in the search.

The part you'd need to take out form the `playlistSearch` variable is going to be something like `show.network%3D90469`. In this specific case it filters for shows by CBC Television, though the specific network ID is not guaranteed to be the same on your system. Plex Tokens [are also retrieved in the browser](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

I run this script via a cron job on my Plex server. But it can be run anywhere that can access your Plex server.