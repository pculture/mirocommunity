#!/usr/bin/env python
#Usage http://uswaretech.com/blog/2008/11/using-paypal-with-django/

## SOURCE: http://djangosnippets.org/snippets/1181/
## Copyright status: (C) 2007 Mike Atlas. The original permission statement is
## below.

# PayPal python NVP API wrapper class.
# This is a sample to help others get started on working
# with the PayPal NVP API in Python. 
# This is not a complete reference! Be sure to understand
# what this class is doing before you try it on production servers!
# ...use at your own peril.

## see https://www.paypal.com/IntegrationCenter/ic_nvp.html
## and
## https://www.paypal.com/en_US/ebook/PP_NVPAPI_DeveloperGuide/index.html
## for more information.

# by Mike Atlas / LowSingle.com / MassWrestling.com, September 2007
# No License Expressed. Feel free to distribute, modify, 
#  and use in any open or closed source project without credit to the author

# Example usage: ===============
#   paypal = PayPal()
#   pp_token = paypal.SetExpressCheckout(100)
#   express_token = paypal.GetExpressCheckoutDetails(pp_token)
#   url= paypal.PAYPAL_URL + express_token
#   HttpResponseRedirect(url) ## django specific http redirect call for payment

#Modified by Shabda


import urllib, md5, datetime
from cgi import parse_qs

class PayPal:
    """ #PayPal utility class"""
    signature_values = {}
    API_ENDPOINT = ""
    PAYPAL_URL = ""
    
    def __init__(self, api_username, api_password, api_signature):
        ## Sandbox values
        self.signature_values = {
        'USER' : api_username,
        'PWD' : api_password,
        'SIGNATURE' : api_signature,
        'VERSION' : '54.0',
        }
        self.API_ENDPOINT = 'https://api-3t.sandbox.paypal.com/nvp' # Sandbox URL, not production
        self.PAYPAL_URL = 'https://www.sandbox.paypal.com/webscr&cmd=_express-checkout&token='
        self.signature = urllib.urlencode(self.signature_values) + "&"

    # API METHODS
    def SetExpressCheckout(self, amount, return_url, cancel_url, **kwargs):
        params = {
            'METHOD' : "SetExpressCheckout",
            'NOSHIPPING' : 1,
            'PAYMENTACTION' : 'Authorization',
            'RETURNURL' : return_url,
            'CANCELURL' : cancel_url,
            'AMT' : amount,
        }
        params.update(kwargs)
        params_string = self.signature + urllib.urlencode(params)
        response = urllib.urlopen(self.API_ENDPOINT, params_string).read()
        response_dict = parse_qs(response)
        response_token = response_dict['TOKEN'][0]
        return response_token
    
    def GetExpressCheckoutDetails(self, token, return_all = False):
        params = {
            'METHOD' : "GetExpressCheckoutDetails",
            'RETURNURL' : 'http://www.yoursite.com/returnurl', #edit this 
            'CANCELURL' : 'http://www.yoursite.com/cancelurl', #edit this 
            'TOKEN' : token,
        }
        params_string = self.signature + urllib.urlencode(params)
        response = urllib.urlopen(self.API_ENDPOINT, params_string).read()
        response_dict = parse_qs(response)
        if return_all:
            return response_dict
        try:
            response_token = response_dict['TOKEN'][0]
        except KeyError:
            response_token = response_dict
        return response_token
    
    def DoExpressCheckoutPayment(self, token, payer_id, amt):
        params = {
            'METHOD' : "DoExpressCheckoutPayment",
            'PAYMENTACTION' : 'Sale',
            'RETURNURL' : 'http://www.yoursite.com/returnurl', #edit this 
            'CANCELURL' : 'http://www.yoursite.com/cancelurl', #edit this 
            'TOKEN' : token,
            'AMT' : amt,
            'PAYERID' : payer_id,
        }
        params_string = self.signature + urllib.urlencode(params)
        response = urllib.urlopen(self.API_ENDPOINT, params_string).read()
        response_tokens = {}
        for token in response.split('&'):
            response_tokens[token.split("=")[0]] = token.split("=")[1]
        for key in response_tokens.keys():
                response_tokens[key] = urllib.unquote(response_tokens[key])
        return response_tokens
        
    def GetTransactionDetails(self, tx_id):
        params = {
            'METHOD' : "GetTransactionDetails", 
            'TRANSACTIONID' : tx_id,
        }
        params_string = self.signature + urllib.urlencode(params)
        response = urllib.urlopen(self.API_ENDPOINT, params_string).read()
        response_tokens = {}
        for token in response.split('&'):
            response_tokens[token.split("=")[0]] = token.split("=")[1]
        for key in response_tokens.keys():
                response_tokens[key] = urllib.unquote(response_tokens[key])
        return response_tokens
                
    def MassPay(self, email, amt, note, email_subject):
        unique_id = str(md5.new(str(datetime.datetime.now())).hexdigest())
        params = {
            'METHOD' : "MassPay",
            'RECEIVERTYPE' : "EmailAddress",
            'L_AMT0' : amt,
            'CURRENCYCODE' : 'USD',
            'L_EMAIL0' : email,
            'L_UNIQUE0' : unique_id,
            'L_NOTE0' : note,
            'EMAILSUBJECT': email_subject,
        }
        params_string = self.signature + urllib.urlencode(params)
        response = urllib.urlopen(self.API_ENDPOINT, params_string).read()
        response_tokens = {}
        for token in response.split('&'):
            response_tokens[token.split("=")[0]] = token.split("=")[1]
        for key in response_tokens.keys():
                response_tokens[key] = urllib.unquote(response_tokens[key])
        response_tokens['unique_id'] = unique_id
        return response_tokens
                
    def DoDirectPayment(self, amt, ipaddress, acct, expdate, cvv2, firstname, lastname, cctype, street, city, state, zipcode):
        params = {
            'METHOD' : "DoDirectPayment",
            'PAYMENTACTION' : 'Sale',
            'AMT' : amt,
            'IPADDRESS' : ipaddress,
            'ACCT': acct,
            'EXPDATE' : expdate,
            'CVV2' : cvv2,
            'FIRSTNAME' : firstname,
            'LASTNAME': lastname,
            'CREDITCARDTYPE': cctype,
            'STREET': street,
            'CITY': city,
            'STATE': state,
            'ZIP':zipcode,
            'COUNTRY' : 'United States',
            'COUNTRYCODE': 'US',
            'RETURNURL' : 'http://www.yoursite.com/returnurl', #edit this 
            'CANCELURL' : 'http://www.yoursite.com/cancelurl', #edit this 
            'L_DESC0' : "Desc: ",
            'L_NAME0' : "Name: ",
        }
        params_string = self.signature + urllib.urlencode(params)
        response = urllib.urlopen(self.API_ENDPOINT, params_string).read()
        response_tokens = {}
        for token in response.split('&'):
            response_tokens[token.split("=")[0]] = token.split("=")[1]
        for key in response_tokens.keys():
            response_tokens[key] = urllib.unquote(response_tokens[key])
        return response_tokens
    
    def CreateRecurringPaymentsProfile(self, token, startdate, desc, period, freq, amt):
        params = {
            'METHOD': 'CreateRecurringPaymentsProfile',
            'PROFILESTARTDATE': startdate,
            'DESC':desc,
            'BILLINGPERIOD':period,
            'BILLINGFREQUENCY':freq,
            'AMT':amt,
            'TOKEN':token,
            'CURRENCYCODE':'USD',
        }
        params_string = self.signature + urllib.urlencode(params)
        response = urllib.urlopen(self.API_ENDPOINT, params_string).read()
        response_dict = parse_qs(response)
        return response_dict
        
        
        
