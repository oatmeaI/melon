import tomllib
import os
from platformdirs import user_config_dir
from melon.constants import APP_NAME, CONFIG_FILE_NAME

DEFAULTS = {
    "serverAddress": "http://127.0.0.1",
    "serverPort": "32400",
    "musicSection": "Music",
    "debug": False,
    "enabled_plugins": ["ExploreRadio", "BetterTrackRadio"],
    "port": 5200,
    "plugin_config": {},
}


class _Config:
    def __init__(self):
        config_dir = user_config_dir(APP_NAME, ensure_exists=True)
        config_file_path = f"{config_dir}/{CONFIG_FILE_NAME}"

        if os.path.exists(config_file_path):
            with open(config_file_path, "rb") as f:
                self.data = tomllib.load(f)
        else:
            self.data = DEFAULTS

        self.serverAddress = self.loadSetting("serverAddress")
        self.serverPort = self.loadSetting("serverPort")
        self.musicSection = self.loadSetting("musicSection")
        self.debug = self.loadSetting("debug")
        self.enabled_plugins = self.loadSetting("enabled_plugins")
        self.port = self.loadSetting("port")
        self.pluginConfig = self.loadSetting("plugin_config")

    def getPluginSettins(self, pluginName):
        if pluginName in self.pluginConfig:
            return self.pluginConfig[pluginName]
        return None

    def loadSetting(self, setting):
        return self.data[setting] if setting in self.data else DEFAULTS[setting]


Config = _Config()
