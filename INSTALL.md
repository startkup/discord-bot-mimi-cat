# Installing TKUAIIC Discord bot

Starting with TKUAIIC Discord bot 1.0.0, it's possible to install and configure
the bot "in-place", as long as you have the necessary prerequisites available.

Required environment as of TKUAIIC Discord bot 1.0.0:

* Device with Python 3 or higher, plus the following libraries and modules:
  * firebase_admin
  * interactions
  * logging
  * os
* Firebase

TKUAIIC Discord bot is developed and tested mainly on Unix/Linux platforms, but
should work on Windows as well.

Don't forget to check the RELEASE-NOTES file...

## In-place manual install

* Set up OS environment variables "DISCORD_TOKEN", "DISCORD_SCOPE"
* Create credentials.json based on the official documentation of Firebase:
  https://firebase.google.com/docs/reference/admin/python/firebase_admin.credentials#certificate
