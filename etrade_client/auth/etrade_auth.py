import webbrowser
from rauth import OAuth1Service
import config

def oauth():
    etrade = OAuth1Service(
        name='etrade',
        consumer_key=config.CONSUMER_KEY,
        consumer_secret=config.CONSUMER_SECRET,
        request_token_url="https://api.etrade.com/oauth/request_token",
        access_token_url="https://api.etrade.com/oauth/access_token",
        authorize_url="https://us.etrade.com/e/t/etws/authorize?key={}&token={}",
        base_url="https://api.etrade.com"
    )

    base_url = config.PROD_BASE_URL

    request_token, request_token_secret = etrade.get_request_token(
        params={"oauth_callback": "oob", "format": "json"})

    authorize_url = etrade.authorize_url.format(etrade.consumer_key, request_token)
    webbrowser.open(authorize_url)

    text_code = input('Enter your code: ')
    session = etrade.get_auth_session(request_token,
                                      request_token_secret,
                                      params={"oauth_verifier": text_code})

    return session, base_url
