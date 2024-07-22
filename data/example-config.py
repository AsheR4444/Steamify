# api id, hash
# Change this file name to config.py
API_ID = 777
API_HASH = ''

DELAYS = {
    'ACCOUNT': [50, 300],  # delay between connections to accounts (the more accounts, the longer the delay)
    'CLAIM': [600, 1800]   # delay in seconds before claim points every 6 hours
}

PROXY_TYPES = {
    "TG": "socks5",  # proxy type for tg client. "socks4", "socks5" and "http" are supported
    "REQUESTS": "socks5"  # proxy type for requests. "http" for https and http proxys, "socks5" for socks5 proxy.
}

# session folder (do not change)
WORKDIR = "sessions/"

# timeout in seconds for checking accounts on valid
TIMEOUT = 30
