import generate_pdf
import tabula
import pandas as pd

def returndata():
    generate_pdf.generate_pdf()
    tables = tabula.read_pdf("info.pdf", pages="all")
    df = pd.concat(tables)
    df = df.astype(str)
    df = df.reset_index(drop=True)
    # pd.set_option('display.max_rows', None)
    # pd.set_option('display.max_columns', None)
    # print(df)
    
    return df

if __name__ == "__main__":
    print(returndata())