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
    proccessed_meal_swipe_data = pd.concat([sortingdata_methods.info_DC(hamp).reset_index(drop=True),sortingdata_methods.info_DC(woo).reset_index(drop=True),sortingdata_methods.info_DC(berk).reset_index(drop=True),sortingdata_methods.info_DC(frank).reset_index(drop=True)],axis=1)
    misc_mealswipes = mealswipes[~mealswipes['Activity_Details'].isin(ALLDININGHALLS)]
    misc_mealswipes = sortingdata_methods.removenums('Activity_Details',misc_mealswipes)
    mics_columns = misc_mealswipes['Activity_Details'].unique()
    for place in mics_columns:
        df = misc_mealswipes[misc_mealswipes['Activity_Details'].str.contains(str(place))]
        proccessed_meal_swipe_data = pd.concat([proccessed_meal_swipe_data,sortingdata_methods.info_DC(df).reset_index(drop=True)],axis=1)
    otherplaces = rawdata[~rawdata['Account_Name'].str.contains("Unlimited")]
    otherplaces = otherplaces[~otherplaces['Activity_Details'].str.contains("WASHER|DRYER|GET FUNDS DEPOSITS|PRNT|Deposit to Student Debit Plan|DC")]
    
    diningdollars = sortingdata_methods.process_unique_values(otherplaces,'Activity_Details')
    proccessed_meal_swipe_data.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner",3:"Late_Night",4:"Total"},inplace=True)
    display(proccessed_meal_swipe_data)
    diningdollars.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner",3:"Total",4:"Total $ Spent"},inplace=True)
    display(diningdollars)



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







#%%

mealswipes.loc[:, 'Balance'] = mealswipes['Balance'].str.replace('$', '')
# dining_dollars.loc[:, 'Amount'] = dining_dollars['Amount'].str.replace('-', '')
mealswipes['Balance'] = pd.to_numeric(mealswipes['Balance'])
mealswipes = mealswipes.reset_index(drop=True)

#mealswipes.drop_duplicates(subset='Balance', keep='first', inplace=True)


hamp = mealswipes[mealswipes['Activity_Details'].isin(["HampDC1","HampDC2","HampDC3","HampDC4"])]
hamp.reset_index(drop=True,inplace=True)
berk = mealswipes[mealswipes['Activity_Details'].isin(["BerkDC1","BerkDC2","BerkDC3","BerkDC4"])]
berk.reset_index(drop=True,inplace=True)
frank = mealswipes[mealswipes['Activity_Details'].isin(["FrankDC1","FrankDC2","FrankDC3","FrankDC4"])]
frank.reset_index(drop=True,inplace=True)
woo = mealswipes[mealswipes['Activity_Details'].isin(["WorcDC1","WorcDC2","WorcDC3","WorcDC4"])]
woo.reset_index(drop=True,inplace=True)

misc_mealswipes = mealswipes[~mealswipes['Activity_Details'].isin(ALLDININGHALLS)]
misc_mealswipes.reset_index(drop=True,inplace=True)


hamp_breakfast = len(hamp[hamp['Date_Time'].dt.time < pd.to_datetime('11:00').time()])
hamp_lunch = len(hamp[(hamp['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (hamp['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
hamp_dinner = len(hamp[hamp['Date_Time'].dt.time >= pd.to_datetime('16:30').time()])
proccessed_meal_swipe_data = pd.DataFrame({"Hamp":[hamp_breakfast,hamp_lunch,hamp_dinner,'NA',len(hamp)]})


berk_breakfast = len(berk[berk['Date_Time'].dt.time < pd.to_datetime('11:00').time()])
berk_lunch = len(berk[(berk['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (berk['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
berk_dinner = len(berk[(berk['Date_Time'].dt.time >= pd.to_datetime('16:30').time()) & (berk['Date_Time'].dt.time < pd.to_datetime('21:00').time())])
berk_latenight = len(berk[(berk['Date_Time'].dt.time >= pd.to_datetime('21:00').time())])
proccessed_meal_swipe_data['Berk'] = [berk_breakfast,berk_lunch,berk_dinner,berk_latenight,len(berk)]

woo_breakfast = len(woo[woo['Date_Time'].dt.time < pd.to_datetime('11:00').time()])
woo_lunch = len(woo[(woo['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (woo['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
woo_dinner = len(woo[(woo['Date_Time'].dt.time >= pd.to_datetime('16:30').time()) & (woo['Date_Time'].dt.time < pd.to_datetime('21:00').time())])
woo_latenight = len(woo[(woo['Date_Time'].dt.time >= pd.to_datetime('21:00').time())])
proccessed_meal_swipe_data['Woo'] = [woo_breakfast,woo_lunch,woo_dinner,woo_latenight,len(woo)]

frank_breakfast = len(frank[frank['Date_Time'].dt.time < pd.to_datetime('11:00').time()])
frank_lunch = len(frank[(frank['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (frank['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
frank_dinner = len(frank[(frank['Date_Time'].dt.time >= pd.to_datetime('16:30').time())])
proccessed_meal_swipe_data['Frank'] = [frank_breakfast,frank_lunch,frank_dinner,'NA',len(frank)]

mics_columns = misc_mealswipes['Activity_Details'].unique()
for place in mics_columns:
    pattern = r'[0-9]'
    micsdf = misc_mealswipes[misc_mealswipes['Activity_Details'].isin([place])]
    num_breakfast = len(micsdf[micsdf['Date_Time'].dt.time < pd.to_datetime('11:00').time()])
    num_lunch = len(micsdf[(micsdf['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (micsdf['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
    num_dinner = len(micsdf[micsdf['Date_Time'].dt.time >= pd.to_datetime('16:30').time()])

    place = re.sub(pattern, '', place)
    proccessed_meal_swipe_data[place] = [num_breakfast,num_lunch,num_dinner,'NA',len(micsdf)]

proccessed_meal_swipe_data.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner",3:"Late_Night",4:"Total"},inplace=True)
total_meal_swpes = proccessed_meal_swipe_data.iloc[4].sum(axis=0)
print(f"youve used {total_meal_swpes} meal swipes")



dining_dollars = rawdata[rawdata['Account_Name'].isin(["UMass Dining Dollars","C Basic Plan","Student Debit Plan"])]
dining_dollars = dining_dollars[~dining_dollars['Activity_Details'].isin(ALLDININGHALLS)]
pattern = r'[0-9]'
dining_dollars.loc[:, 'Amount'] = dining_dollars['Amount'].str.replace('$', '')
dining_dollars.loc[:, 'Amount'] = dining_dollars['Amount'].str.replace('-', '')
dining_dollars.loc[:,'Activity_Details'] = dining_dollars['Activity_Details'].apply(lambda x: re.sub(pattern, '', str(x)))
dining_dollars.loc[:, 'Activity_Details'] = dining_dollars['Activity_Details'].str.strip()
dining_dollars = dining_dollars[~dining_dollars['Activity_Details'].str.contains("WASHER|DRYER|GET FUNDS DEPOSITS|PRNT")]
dining_dollars.loc[:, 'Amount'] = pd.to_numeric(dining_dollars['Amount'])
#display(dining_dollars)
proccessed_dining_dolla_data = pd.DataFrame()
mics_columns = dining_dollars['Activity_Details'].unique()
#display(dining_dollars)
for place in mics_columns:
    
    micsdf = dining_dollars[dining_dollars['Activity_Details'].isin([place])]
    num_breakfast = len(micsdf[micsdf['Date_Time'].dt.time < pd.to_datetime('11:00').time()])
    num_lunch = len(micsdf[(micsdf['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (micsdf['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
    num_dinner = len(micsdf[micsdf['Date_Time'].dt.time >= pd.to_datetime('16:30').time()])
    allsum = micsdf['Amount'].sum()
    if(micsdf['Account_Name'] == "C Basic Plan").any():
        allsum *=12
    proccessed_dining_dolla_data[place] = [num_breakfast,num_lunch,num_dinner,len(micsdf),f"${format(allsum,'.2f')}"]
proccessed_dining_dolla_data.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner",3:"Total",4:"Total $ Spent"},inplace=True)



print(f"You have gone to hamp {proccessed_meal_swipe_data['Hamp']['Total']} times")
print(f"You have gone to berk {proccessed_meal_swipe_data['Berk']['Total']} times")
print(f"You have gone to frank {proccessed_meal_swipe_data['Frank']['Total']} times")
print(f"You have gone to woo {proccessed_meal_swipe_data['Woo']['Total']} times")
print(f"youve used {len(mealswipes)} meal swipes")


