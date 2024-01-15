from selenium import webdriver
import json
import time
def updatecookies():
    # Create a new instance of the Firefox WebDriver (you can use other drivers like Chrome, etc.)
    driver = webdriver.Chrome()

    # Open the website
    driver.get("https://login.microsoftonline.com/7bd08b0b-3395-4dc1-94bb-d0b2e56a497f/saml2?SAMLRequest=jZJLT8MwEIT%2FSuR74sRJmsRqKpX2QKUCVVM4cEG247SWHLt4HR7%2Fnj5AlEvFeWe%2F2Rl7DKzXezod%2FM6s5esgwQcfvTZAT4MaDc5Qy0ABNayXQL2gzfRuSUkU072z3gqrUTAFkM4ra2bWwNBL10j3poR8XC9rtPN%2BDxTjrfSR4Na1kbA9HnoGgJud4txq6XcRgMVHNMGrh2aDgvnhFmXYkfrL0HarTNQr4SzYzlujlZEnXsHbuOQxD9O0ysOsFUlYZZyHbcyJzEcsq4oOH0MRFCzmNXqpRqzrMiGLrCxHcZ6QqiyyPE%2FjomNxWpUHGcAgFwY8M75GJCZpmCQhKTZJTvOMJuQZBavvDm6UaZXZXi%2BMn0VAbzebVXiO%2BSQdnCIeBGgyPl5IT8bu4iGuY9lP%2B2jy%2F67H%2BMLq7Lun9wf2Yr6yWonPYKq1fZ85ybysUYLw5Lzy97dMvgA%3D&RelayState=https%3A%2F%2Fget.cbord.com%2Fumass%2Ffull%2Flogin.php&SigAlg=http%3A%2F%2Fwww.w3.org%2F2000%2F09%2Fxmldsig%23rsa-sha1&Signature=xGf9kw6QG%2BFQpFQsqLW2egtQrFmBEXTq0Lv7H8v4Su0J73y5oiUn56J7CN0jNpDehbFKJepdlIdOI4h%2BjTrM86JZGXAz7k5Nr3URXFWLE5GlwZMCBdF0dCN7SDhl%2B1s%2FW6M0GvMS%2FSbzB9a9aMYRwUrpjaLO4SktpXpp0LyvWKzYDIceYULcsEgMR7HEiu1%2BlIrlqlZhge8URrU2dK5tzeJbUFe3XLbFT5w2matCh05GeR4NGuGpYtcj1AYZETkufRNnXqPo9Il4CKtvEFFueDK%2BhSpQxq%2FMAq3poxlGE3DDLgH5HKTL%2BDVEZQfu5zD5enO3XqvDrGKmj9Fam%2FGMe9eI0m1nI5LTrmdw%2BbTkp5pSgQZ0mFpYk%2FAtD0vwojK70CE0gaTnJkHWhWIaJChkPWpCqdc5PhE3tsPAg%2BnwtHMFZlnR1deztvi5cL0oLZ6lRCPAkjsjGqMez2%2Fe1HoezO%2BvVLg52wzaJ%2BpuPx5HINuP0zMHjxgV%2FxNat4oe01Wh%2B%2F2avSrVUJE%2FwVHttiy5Xw85BMENl0qMWOTFRb4TQprq4BqCxgiH2rhIcG7i0c2BbA5JLWf%2B2PGgjcAzE9%2FL%2FayjzxvD8GSIVvVFNGjmySumQWd4Q%2Bc50%2FwVie%2FPDvrd%2FqscXk2p%2BzLZo7BkRzeHKBCzsgfp5fzdLy0%2BjGIZ7B8%3D&sso_reload=true")

    # Perform some actions if needed

    # Get all the cookies
    while(True):
        if(driver.current_url == "https://get.cbord.com/umass/full/funds_home.php"):
            cookies = driver.get_cookies()
            driver.quit()
            break
    return cookies

    




