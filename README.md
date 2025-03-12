# Melon In The Middle (for Plex) 🐶
Melon In The Middle (`melon` for short) is a tool that allows you to extend the functionality of your Plex server in almost any way imaginable.

## How?
`melon` is a proxy server that sits between your Plex server and your Plex client, allowing you to intercept & modify requests to, and responses from the Plex server. This allows you to do things like add custom Stations, change what buttons do or how metadata is displayed...or just about anything else.

## Usage
Setting up `melon` takes a little bit of work, because we need to trick Plex into always connecting via `melon` instead of connecting directly to the Plex server. There are 3 main steps:
### 1. Configure a Reverse Proxy to your Plex server
1. **Set up a reverse proxy to your Plex server:** There are lots of different guides on how to do this floating around - I use [Caddy](https://caddyserver.com/), which is pretty easy to set up.
2. **Disable Remote Access:** In your Plex server settings, disable Remote Access (don't worry, you'll still be able to access your server remotely)
3. **Add your reverse proxy to Plex:** In the Network tab, click "Show Advanced", find the "Custom server access URLs" field, and add your reverse proxy URL (this step is probably included in many of the Plex reverse proxy guides out there, if you've done it already then you can skip this step). You may also want to check the `Treat WAN IP As LAN Bandwidth` box on this page - it's not required for `melon` to work though.
4. **Force Plex to use the reverse proxy even on LAN:** Following the [Plex documentation on changing hidden settings](https://support.plex.tv/articles/201105343-advanced-hidden-server-settings/) to set `allowLocalhostOnly 1` (on my Mac, I ran `defaults write com.plexapp.plexmediaserver allowLocalhostOnly 1`). This tells Plex not to allow LAN connections, forcing your clients to to connect via the reverse proxy over the Internet.

At this point, you should be able to use Plex as normal, but all connections will be funneled through your reverse proxy.

### 2. Set your reverse proxy to send traffic to Melon
1. Update your reverse proxy configuration to send all traffic to `localhost:5200` (the port that `melon` uses) instead of to your Plex server.
2. Set your proxy to send traffic to Plex if `melon` returns an error.
This part is a little weird, but not that complicated. My `Caddyfile` looks like this:
```
plex.mydomain.com {
  reverse_proxy localhost:5200 {
    @error status 500 404
    handle_response @error {
      reverse_proxy localhost:32400 
    }
  }
}
```
This way, if `melon` gets a request it doesn't want to (or doesn't know how to) handle, we just send it straight through to Plex. This allows us to only mess around with the specific requests we're interested in, and let the actual Plex server handle everything else.

At this point, your Plex clients will probably show your server as inaccessible - that's okay, we just need to start up `melon`!

### 3. Almost done - start up Melon In The Middle!
0. Ensure [Poetry](https://python-poetry.org/) is installed
1. `git clone` this repo
2. Run `poetry install` in the project root
3. Run `poetry start`
(In the future, we'll distribute an actual binary and you won't need to clone the repo or use Poetry...but for now...)
If everything worked, your Plex clients should be able to access your server again, and you should see a new Station named "Explore Radio" in the Music section of your library.
That station is created by the Explore Station plugin...

## Plugins
Extensions to Plex functionality served by Melon are handled by plugins. Currently there is only one plugin - Explore Radio - and all plugins must be bundled with Melon. In the future, there will be more plugins which over more functionlality, and a way to install plugins not bundled with Melon (see the Roadmap below).

### ExploreRadio
Explore Radio is the reason I created Melon. The Explore Radio Plugin adds a new Station to your Music library which tries to play a pretty even mix of songs you've rated highly and songs you've never heard before, while maintaining a vibe (using Plex's sonic similarity feature).

### Options
`ExploreRadio` offers one option - `station_name` - which determines what the Explore station will be named in the UI.

## Config
Melon In the Middle usually does not require any configuration, but a config file is available in case you want to tweak anything.
The file lives at the `user_config_dir` specified by [platformdirs](https://pypi.org/project/platformdirs/) - on macOS, it's `~/Library/Application Support/melon/config.toml`.
The available options and their defaults are:
|Option name|What it does|Default value|
|-----------|------------|-------------|
|`serverAddress`|The address of your Plex server.|`http://127.0.0.`|
|`serverPort`|The port your Plex server is listening on.|`32400`|
|`musicSection`|The name of your Music library on your Plex server|`Music`|
|`debug`|Turns on some extra logging and hot reloading|`False`|
|`enabled_plugins`|A list of bundled plugins to that should be enabled|`["ExploreRadio"]`|
|`port`|The port that `melon` should listen on|`5200`|

### Plugin Config
Some plugins offer their own config options. These can be specified under `[plugin_config.{Plugin Name}]` in the `config.toml`

### Example config.toml:
```toml
enabled_plugins = ["ExploreRadio"]

[plugin_config.ExploreRadio]
station_name = "Cool Guys Radio"
```

## Roadmap
- [ ] 2nd bundled plugin - better Track Radio
- [ ] Plugin developer documentation
- [ ] Installing un-bundled plugins
- [ ] An actual build process & binary distribution
- [ ] Better log messages / log to a file

## What's with the name?
- It's a **man in the middle** proxy.
- Plex is an app for watching TV; **Malcolm In The Middle** is a famous TV show.
- **Melon** is my dog's name (and she likes to be in the middle of the bed)

![IMG_5578](https://github.com/user-attachments/assets/d83e76ad-f239-4128-a6d1-3fe6e10c2db8)
