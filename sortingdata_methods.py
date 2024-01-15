import readpdf_data
import pandas as pd
import numpy as np
import re

# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)

def preproccessrawdata(rawdata):
    rawdata.rename(columns={"Account Name:": "Account_Name", "Date & Time": "Date_Time", "Activity Details": "Activity_Details", "Amount ($ / Meals)": "Amount"}, inplace=True)
    for column in rawdata.columns:
        if rawdata[column].dtype == 'O':
            rawdata[column] = rawdata[column].str.strip()
    #rawdata = rawdata[rawdata['Activity_Details'] != 'Meal Plan Office']
    rawdata = rawdata[~rawdata['Activity_Details'].str.contains("GET FUNDS DEPOSITS|Deposit to Student Debit Plan|PatronImport Location|Meal Plan Office")]
    rawdata.reset_index(drop=True, inplace=True)
    rawdata['Date_Time'] = rawdata['Date_Time'].str.replace(r'(AM|PM).*$', r'\1', regex=True)
    rawdata['Date_Time'] = pd.to_datetime(rawdata['Date_Time'],format="%B %d, %Y, %I:%M%p")
    rawdata['Amount'] = rawdata['Amount'].str.split('-').str[1]
    rawdata.drop_duplicates(keep='first', inplace=True)
    return rawdata

def is_mealswipes(rawdata):
    return (rawdata['Account_Name'] == "E Unlimited 250").any() | (rawdata['Account_Name'] == "M Unlimited DC").any() | (rawdata['Account_Name'] == "C Basic Plan").any()


def unlimitedmealswipedata(rawdata):
    mealswipes = rawdata[rawdata['Account_Name'].isin(["E Unlimited 250","M Unlimited DC","C Basic Plan"])]
    return mealswipes

def dining_hall_data(rawdata):
    #mealswipes = rawdata[rawdata['Account_Name'].isin(["E Unlimited 250","M Unlimited DC"])]
    hamp = rawdata[rawdata['Activity_Details'].isin(["HampDC1","HampDC2","HampDC3","HampDC4"])]
    berk = rawdata[rawdata['Activity_Details'].isin(["BerkDC1","BerkDC2","BerkDC3","BerkDC4"])]
    frank = rawdata[rawdata['Activity_Details'].isin(["FrankDC1","FrankDC2","FrankDC3","FrankDC4"])]
    woo = rawdata[rawdata['Activity_Details'].isin(["WorcDC1","WorcDC2","WorcDC3","WorcDC4"])]

    return hamp,berk,frank,woo

def misc_meal_swipe_data(mealswipes):
    alldininghalls = ["HampDC1","HampDC2","HampDC3","HampDC4","BerkDC1","BerkDC2","BerkDC3","BerkDC4","FrankDC1","FrankDC2","FrankDC3","FrankDC4","WorcDC1","WorcDC2","WorcDC3","WorcDC4"]
    misc_mealswipes = mealswipes[~mealswipes['Activity_Details'].isin(alldininghalls)]
    return misc_mealswipes

def removenums(column,data):
    pattern = r'[0-9]'
    data.loc[:,column] = data[column].apply(lambda x: re.sub(pattern, '', str(x)))
    data.loc[:, column] = data[column].str.strip()
    return data


def info_DC(data):
    if not data.empty:
        pattern = r'[0-9]'
        name = str(data['Activity_Details'].iloc[0])
        name = re.sub(pattern, '', name)
        breakfast = num_breakfast(data)
        lunch = num_lunch(data)
        dinner = num_dinner(data)
        latenight = num_latenight(data)
        grabngo = num_grabngo(data)
        return pd.DataFrame({name:[breakfast,lunch,dinner,latenight,grabngo,len(data)]}).reset_index(drop=True)

def num_breakfast(data):
    if(data['Activity_Details'].str.contains("Frank|Worc")).any():
        data = data[~data['Activity_Details'].str.contains("1")]
    return len(data[data['Date_Time'].dt.time < pd.to_datetime('11:00').time()])

def num_lunch(data):
    if(data['Activity_Details'].str.contains("Frank|Worc")).any():
        data = data[~data['Activity_Details'].str.contains("1")]
    return len(data[(data['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (data['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
    
def num_dinner(data):
    if(data['Activity_Details'].str.contains("Frank|Worc")).any():
        data = data[~data['Activity_Details'].str.contains("1")]
    return len(data[(data['Date_Time'].dt.time >= pd.to_datetime('16:30').time()) & (data['Date_Time'].dt.time < pd.to_datetime('21:00').time())])

def num_latenight(data):
    if(data['Activity_Details'].str.contains("Berk|Worc")).any():
        data = data[~data['Activity_Details'].str.contains("1")]
        num = len(data[(data['Date_Time'].dt.time >= pd.to_datetime('21:00').time())])
        return num
    else:
        return 'NA'
    
def num_grabngo(data):
    if(data['Activity_Details'].str.contains("Frank|Worc")).any():
        data = data[data['Activity_Details'].str.contains("1")]
        num = len(data)
        return num
    else:
        return 'NA'

def totaldollars(data):
    data.loc[:, 'Amount'] = data['Amount'].str.replace('$', '')
    data.loc[:, 'Amount'] = data['Amount'].str.replace('-', '')
    data.loc[:, 'Amount'] = pd.to_numeric(data['Amount'])
    allsum = data['Amount'].sum()
    if(data['Account_Name'].str.contains("C Basic Plan|YCMP")).any():
        allsum *=12
    return allsum

def process_unique_values(df, column_name):
    processed_data = pd.DataFrame()
    df = removenums(column_name,df)
    unique_values = df[column_name].unique()
    
    for value in unique_values:
        sub_df = df[df[column_name].str.contains(str(value))]
        if not sub_df.empty:
            processed_data = pd.concat([processed_data,info(sub_df).reset_index(drop=True)], axis=1)

    return processed_data

def info(data):
    if not data.empty:
        name = str(data['Activity_Details'].iloc[0])
        breakfast = num_breakfast(data)
        lunch = num_lunch(data)
        dinner = num_dinner(data) 
        if(type(num_latenight(data)) is int):
            dinner+= num_latenight(data)
        totaldollar = totaldollars(data)
        return pd.DataFrame({name:[int(breakfast),int(lunch),int(dinner),int(len(data)),totaldollar]}).reset_index(drop=True)


def fillEmpty(data):
    DCs = ['HampDC','WorcDC','FrankDC','BerkDC']
    for dininghall in DCs:
        if dininghall not in data.columns:
            data[dininghall] = {"Breakfast" : 0,"Lunch" : 0,"Dinner" : 0,"Late_Night" : 0,"GrabNGo" : 0,"Total" : 0}
    return data


if __name__ == "__main__":
    rawdata = readpdf_data.returndata()
    rawdata = preproccessrawdata(rawdata)
    if(is_mealswipes(rawdata)):
        hamp,berk,frank,woo = dining_hall_data(rawdata)
        print(hamp)
        

























# mealswipes = rawdata[rawdata['Account Name:'].isin(["E Unlimited 250","M Unlimited DC"])]
# mealswipes = mealswipes.reset_index(drop=True)
# mealswipes.drop_duplicates(subset='Balance', keep='first', inplace=True)

# #print(mealswipes)
# hamp = mealswipes[mealswipes['Activity Details'].isin(["HampDC1","HampDC2","HampDC3","HampDC4"])]
# hamp.reset_index(drop=True,inplace=True)
# berk = mealswipes[mealswipes['Activity Details'].isin(["BerkDC1","BerkDC2","BerkDC3","BerkDC4"])]
# berk.reset_index(drop=True,inplace=True)
# frank = mealswipes[mealswipes['Activity Details'].isin(["FrankDC1","FrankDC2","FrankDC3","FrankDC4"])]
# frank.reset_index(drop=True,inplace=True)
# woo = mealswipes[mealswipes['Activity Details'].isin(["WorcDC1","WorcDC2","WorcDC3","WorcDC4"])]
# woo.reset_index(drop=True,inplace=True)

# alldininghalls = ["HampDC1","HampDC2","HampDC3","HampDC4","BerkDC1","BerkDC2","BerkDC3","BerkDC4","FrankDC1","FrankDC2","FrankDC3","FrankDC4","WorcDC1","WorcDC2","WorcDC3","WorcDC4"]
# misc_mealswipes = mealswipes[~mealswipes['Activity Details'].isin(alldininghalls)]
# misc_mealswipes.reset_index(drop=True,inplace=True)

# print(misc_mealswipes)

# print(f"You have gone to hamp {len(hamp)} times")
# print(f"You have gone to berk {len(berk)} times")
# print(f"You have gone to frank {len(frank)} times")
# print(f"You have gone to woo {len(woo)} times")
# print(f"youve used {len(mealswipes)-1} meal swipes")