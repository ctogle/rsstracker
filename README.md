# rsstracker
Terminal application for monitoring multiple RSS feeds.

URLs of RSS feeds of interest are specified in a file given as the --urlspath option (default: "./urls").
The output associated with one RSS feed is shown at a time, and the active feed can be cycled with the "[" and "]" keys.
The history of each feed can be stored and reused in the directory given as the --feedcache option (default: "./.rsscache/").
The default active feed can be specified with the --current option (defaults to the first feed in in the URLs file).
Additional navigation keys for the active feed are specified at the bottom of the terminal.

