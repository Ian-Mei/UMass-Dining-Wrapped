import testpdf
import pandas as pd
import numpy as np

rawdata = testpdf.getdata()
#print(rawdata)

mealswipes = rawdata[rawdata['Account Name:'] == "E Unlimited 250"]
mealswipes = mealswipes.reset_index(drop=True)
hamp = mealswipes[mealswipes['Activity Details'].isin(["HampDC1","HampDC2","HampDC3","HampDC4"])]
hamp.reset_index(drop=True,inplace=True)
berk = mealswipes[mealswipes['Activity Details'].isin(["BerkDC1","BerkDC2","BerkDC3","BerkDC4"])]
berk.reset_index(drop=True,inplace=True)
frank = mealswipes[mealswipes['Activity Details'].isin(["FrankDC1","FrankDC2","FrankDC3","FrankDC4"])]
frank.reset_index(drop=True,inplace=True)
woo = mealswipes[mealswipes['Activity Details'].isin(["WorcDC1","WorcDC2","WorcDC3","WorcDC4"])]
woo.reset_index(drop=True,inplace=True)

alldininghalls = ["HampDC1","HampDC2","HampDC3","HampDC4","BerkDC1","BerkDC2","BerkDC3","BerkDC4","FrankDC1","FrankDC2","FrankDC3","FrankDC4","WorcDC1","WorcDC2","WorcDC3","WorcDC4"]
misc_mealswipes = mealswipes[~mealswipes['Activity Details'].isin(alldininghalls)]
misc_mealswipes.reset_index(drop=True,inplace=True)

print(misc_mealswipes)

print(f"You have gone to hamp {len(hamp)} times")
print(f"You have gone to berk {len(berk)} times")
print(f"You have gone to frank {len(frank)} times")
print(f"You have gone to woo {len(woo)} times")