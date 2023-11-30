#%%
import readpdf_data
import pandas as pd
import re
import sortingdata_methods

ALLDININGHALLS = ["HampDC1","HampDC2","HampDC3","HampDC4","BerkDC1","BerkDC2","BerkDC3","BerkDC4","FrankDC1","FrankDC2","FrankDC3","FrankDC4","WorcDC1","WorcDC2","WorcDC3","WorcDC4"]

rawdata = readpdf_data.returndata()

rawdata = sortingdata_methods.preproccessrawdata(rawdata)

#mealswipedata (only if they have unlimted)
#dining hall data
#dining dollor data -- anywhere that isnt dininghall/ printing/washing
#washingmachine data
#printing data



if(sortingdata_methods.is_unlimited(rawdata)):
    mealswipes = sortingdata_methods.unlimitedmealswipedata(rawdata)
    num_mealswipes_used = len(mealswipes)

    hamp,berk,frank,woo = sortingdata_methods.dining_hall_data(mealswipes)
    proccessed_meal_swipe_data = pd.concat([sortingdata_methods.info_DC(hamp),sortingdata_methods.info_DC(woo),sortingdata_methods.info_DC(berk),sortingdata_methods.info_DC(frank)],axis=1)
    misc_mealswipes = mealswipes[~mealswipes['Activity_Details'].isin(ALLDININGHALLS)]
    misc_mealswipes = sortingdata_methods.removenums('Activity_Details',misc_mealswipes)
    mics_columns = misc_mealswipes['Activity_Details'].unique()
    for place in mics_columns:
        df = misc_mealswipes[misc_mealswipes['Activity_Details'].str.contains(str(place))]
        proccessed_meal_swipe_data = pd.concat([proccessed_meal_swipe_data,sortingdata_methods.info_DC(df).reset_index(drop=True)],axis=1)
    otherplaces = rawdata[~rawdata['Account_Name'].str.contains("Unlimited")]
    otherplaces = otherplaces[~otherplaces['Activity_Details'].str.contains("WASHER|DRYER|GET FUNDS DEPOSITS|PRNT|Deposit to Student Debit Plan|DC")]
    otherplaces = sortingdata_methods.removenums('Activity_Details',otherplaces)
    diningdollars = sortingdata_methods.process_unique_values(otherplaces,'Activity_Details')
    proccessed_meal_swipe_data.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner",3:"Late_Night",4:"GrabNGo",5:"Total"},inplace=True)
    display(proccessed_meal_swipe_data)
    diningdollars.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner",3:"Total",4:"Total $ Spent"},inplace=True)
    display(diningdollars)
    print(f"Youve used {num_mealswipes_used} meal swipes")




else:
    #mealswipes = rawdata[rawdata['Activity_Details'].isin(ALLDININGHALLS)]
    hamp,berk,frank,woo = sortingdata_methods.dining_hall_data(rawdata)
    proccessed_meal_swipe_data = pd.concat([sortingdata_methods.info_DC(hamp).reset_index(drop=True),sortingdata_methods.info_DC(woo).reset_index(drop=True),sortingdata_methods.info_DC(berk).reset_index(drop=True),sortingdata_methods.info_DC(frank).reset_index(drop=True)],axis=1)
    otherplaces = rawdata[~rawdata['Activity_Details'].str.contains("WASHER|DRYER|GET FUNDS DEPOSITS|PRNT|Deposit to Student Debit Plan|DC")]
    
    diningdollars = sortingdata_methods.process_unique_values(otherplaces,'Activity_Details')
    proccessed_meal_swipe_data.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner",3:"Late_Night",4:"Total"},inplace=True)
    display(proccessed_meal_swipe_data)
    diningdollars.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner",3:"Total",4:"Total $ Spent"},inplace=True)
    display(diningdollars)

laundry = rawdata[rawdata['Activity_Details'].str.contains("WASHER|DRYER")]
laundrywash = rawdata[rawdata['Activity_Details'].str.contains("WASHER")]
laundrydry = rawdata[rawdata['Activity_Details'].str.contains("DRYER")]
#display(laundrydry)
most_common_dryer = laundrydry['Activity_Details'].value_counts().idxmax()
#display(laundrywash)
most_common_washer = laundrywash['Activity_Details'].value_counts().idxmax()
most_common_day = laundry['Date_Time'].dt.day_name().value_counts().idxmax()
print(f"Your favorite dryer is {most_common_dryer}")
print(f"Your favorite washer is {most_common_washer}")
print(f"Your favorite day to do laundry is {most_common_day}")

# %%
