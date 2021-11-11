import sys

import numpy as np
import pandas as pd
import sqlalchemy
from plotly import express as px
from plotly import figure_factory as ff
from plotly import graph_objects as go
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.tree import DecisionTreeClassifier


def is_continuous(data, col):
    # This Function takes in a column of a pandas data frame and returns a boolean depending on if the column variables
    # are continuous or not.

    # len(data[col].unique()) <= 0.1 * len(data[col]

    if (
        (len(data[col].unique()) < 8)
        or data[col].dtype == "O"
        or data[col].dtype == str
    ):
        return False
    return True


# This function is from teaching.mrsharky slides
def cat_cont_correlation_ratio(categories, values):
    """
    Correlation Ratio: https://en.wikipedia.org/wiki/Correlation_ratio
    SOURCE:
    1.) https://towardsdatascience.com/the-search-for-categorical-correlation-a1cf7f1888c9
    :param categories: Numpy array of categories
    :param values: Numpy array of values
    :return: correlation
    """
    f_cat, _ = pd.factorize(categories)
    cat_num = np.max(f_cat) + 1
    y_avg_array = np.zeros(cat_num)
    n_array = np.zeros(cat_num)
    for i in range(0, cat_num):
        cat_measures = values[np.argwhere(f_cat == i).flatten()]
        n_array[i] = len(cat_measures)
        y_avg_array[i] = np.average(cat_measures)
    y_total_avg = np.sum(np.multiply(y_avg_array, n_array)) / np.sum(n_array)
    numerator = np.sum(
        np.multiply(n_array, np.power(np.subtract(y_avg_array, y_total_avg), 2))
    )
    denominator = np.sum(np.power(np.subtract(values, y_total_avg), 2))
    if numerator == 0:
        eta = 0.0
    else:
        eta = np.sqrt(numerator / denominator)
    return eta


def brute_force(pred1, pred2, resp, data):
    """
    This function takes two predictors as string, the response, and the data set being used
    and it calculates the mean of the response in different bins and weights those bins with
    the population ratio of that bin. It returns a matrix of the unweighted mean of response
    in each cell as well as the sum of the squared mean difference as an evaluation metric
    """
    copy_data = data.copy()  # copy the data so not to change it outside the function
    resp_mean = data[resp].mean()  # mean of the response of the whole dataset

    if is_continuous(data, pred1):
        copy_data["bins1"] = pd.cut(copy_data[pred1], 10, labels=False)
        if is_continuous(data, pred2):
            copy_data["bins2"] = pd.cut(
                copy_data[pred2], 10, labels=False
            )  # spliting both columns into 10 bins
            calc_matrix = np.zeros((10, 10))
            pop_ratio_matrix = np.zeros_like((calc_matrix))
            for x_1, val1 in enumerate(copy_data["bins1"].unique()):
                for x_2, val2 in enumerate(copy_data["bins2"].unique()):
                    bin_mean = copy_data[resp][
                        (copy_data["bins1"] == x_1) & (copy_data["bins2"] == x_2)
                    ].mean()
                    pop_ratio = (
                        len(copy_data[resp][copy_data["bins1"] == x_1])
                        / len(copy_data[resp])
                        * len(copy_data[resp][copy_data["bins2"] == x_2])
                        / len(copy_data[resp])
                    )
                    pop_ratio_matrix[x_1, x_2] = pop_ratio
                    calc_matrix[x_1, x_2] = bin_mean
        else:
            calc_matrix = np.zeros(
                (10, len(copy_data[pred2].unique()))
            )  # using the unique values of the column
            pop_ratio_matrix = np.zeros_like(
                (calc_matrix)
            )  # as the bins for categorical
            for x_1, val1 in enumerate(copy_data["bins1"].unique()):
                for x_2, val2 in enumerate(copy_data[pred2].unique()):
                    bin_mean = copy_data[resp][
                        (copy_data["bins1"] == x_1) & (copy_data[pred2] == val2)
                    ].mean()
                    pop_ratio = (
                        len(copy_data[resp][copy_data["bins1"] == x_1])
                        / len(copy_data[resp])
                        * len(copy_data[resp][copy_data[pred2] == val2])
                        / len(copy_data[resp])
                    )
                    pop_ratio_matrix[
                        x_1, x_2
                    ] = pop_ratio  # matrix of the population ratio to be used in later calc
                    calc_matrix[x_1, x_2] = bin_mean
    else:
        if is_continuous(data, pred2):
            calc_matrix = np.zeros((len(copy_data[pred1].unique()), 10))
            pop_ratio_matrix = np.zeros_like((calc_matrix))
            copy_data["bins2"] = pd.cut(copy_data[pred2], 10, labels=False)
            for x_1, val1 in enumerate(copy_data[pred1].unique()):
                for x_2, val2 in enumerate(copy_data["bins2"].unique()):
                    bin_mean = copy_data[resp][
                        (copy_data[pred1] == val1) & (copy_data["bins2"] == x_2)
                    ].mean()
                    pop_ratio = (
                        len(copy_data[resp][copy_data[pred1] == val1])
                        / len(copy_data[resp])
                        * len(copy_data[resp][copy_data["bins2"] == x_2])
                        / len(copy_data[resp])
                    )
                    pop_ratio_matrix[x_1, x_2] = pop_ratio
                    calc_matrix[x_1, x_2] = bin_mean
        else:
            calc_matrix = np.zeros(
                (len(copy_data[pred1].unique()), len(copy_data[pred2].unique()))
            )
            pop_ratio_matrix = np.zeros_like((calc_matrix))
            for x_1, val1 in enumerate(copy_data[pred1].unique()):
                for x_2, val2 in enumerate(copy_data[pred2].unique()):
                    bin_mean = copy_data[resp][
                        (copy_data[pred1] == val1) & (copy_data[pred2] == val2)
                    ].mean()
                    pop_ratio = (
                        len(copy_data[resp][copy_data[pred1] == val1])
                        / len(copy_data[resp])
                        * len(copy_data[resp][copy_data[pred2] == val2])
                        / len(copy_data[resp])
                    )
                    pop_ratio_matrix[x_1, x_2] = pop_ratio
                    calc_matrix[x_1, x_2] = bin_mean

    calc_matrix = np.nan_to_num(calc_matrix)  # changing all the NANs to 0.

    avg_mean_diff = (
        ((calc_matrix - resp_mean) ** 2) * pop_ratio_matrix
    ).sum()  # using the pop matrix for easy scaling of
    # of the original matrix
    return calc_matrix, avg_mean_diff


def plot_catp_catr(pred, resp, data):
    # This function plots a heatmap of the two catigrocial variables
    copy_data = data.copy()  # The copy makes it so i dont change the outside data
    # copy_data[pred] = copy_data[pred].astype("string")
    conf_matrix = confusion_matrix(copy_data[pred], copy_data[resp])
    fig = go.Figure(data=go.Heatmap(z=conf_matrix, zmin=0, zmax=conf_matrix.max()))
    fig.update_layout(
        title=f"Categorical Predictor: {pred} by Categorical Response {resp}",
        xaxis_title="Response",
        yaxis_title="Predictor",
    )
    file = f"./plots/cat_{resp}_by_cat_{pred}_heatmap.html"
    # fig.show()
    fig.write_html(
        file=f"./plots/cat_{resp}_by_cat_{pred}_heatmap.html",
        include_plotlyjs="cdn",
    )
    return file


def plot_contp_catr(pred, resp, data):
    copy_data = data.copy()
    # copy_data[resp] = copy_data[resp].astype("string")
    cat_resp_list = list(copy_data[resp].unique())
    n = len(cat_resp_list)
    cont_pred_list = [
        copy_data[pred][copy_data[resp] == resp_name] for resp_name in cat_resp_list
    ]
    fig_2 = go.Figure()
    for curr_hist, curr_group in zip(cont_pred_list, cat_resp_list):
        fig_2.add_trace(
            go.Violin(
                x=np.repeat(curr_group, n),
                y=curr_hist,
                name=str(curr_group),
                box_visible=True,
                meanline_visible=True,
            )
        )
    file = f"./plots/cat_{resp}_cont_{pred}_violin_plot.html"
    fig_2.update_layout(
        title=f"Continuous Predictor: {pred} by Categorical Response: {resp}",
        xaxis_title="Response",
        yaxis_title="Predictor",
    )
    # fig_2.show()
    fig_2.write_html(
        file=f"./plots/cat_{resp}_cont_{pred}_violin_plot.html",
        include_plotlyjs="cdn",
    )
    return file


def cor_calc_cont_cont(data, pred_lst, resp):

    cor_tbl = pd.DataFrame(
        columns=[
            "Predictor 1",
            "pred1_plot",
            "Predictor 2",
            "pred2_plot",
            "Correlation Metric",
        ]
    )
    cor_matrix = np.zeros(
        (len(pred_lst), len(pred_lst))
    )  # makes 2d matrix to hold values
    i = 0
    # path = "/Users/dylanmather/Documents/Grad_School/Fall_21_temp/BDA696_PythonProject2/Assignments/"
    # The begining of the file path of where to save the tables
    for x, pred1 in enumerate(pred_lst):
        for y, pred2 in enumerate(pred_lst):
            cor_metric = stats.pearsonr(data[pred1], data[pred2])
            # These next few lines plot the indivudal categories by the response. They return file adresses to be put
            # into the table later.
            if is_continuous(data, resp):
                # file1_name = plot_contp_contr(pred1, resp, data)
                # file2_name = plot_contp_contr(pred2, resp, data)
                pass
            else:
                file1_name = plot_contp_catr(pred1, resp, data)
                file2_name = plot_contp_catr(pred2, resp, data)
            # adding all the calculated values to the table
            cor_tbl.loc[i] = [
                pred1,
                file1_name,
                pred2,
                file2_name,
                cor_metric[0],
            ]
            cor_matrix[x, y] = round(cor_metric[0], 4)
            i += 1
    sort_tbl = cor_tbl.sort_values(by="Correlation Metric", ascending=False)
    # this sorts the table by the correlation metric
    return sort_tbl, cor_matrix


def mean_diff_tbl(pred, resp, data):
    # This calculates the mean difference of the response of 1D so one predictor and one response
    df = pd.DataFrame(
        columns=[
            "(i)",
            "Bin_Pop",
            "Bin_Mean",
            "Pop_Mean",
            "Pop_Proportion",
            "Mean_Sq_Diff",
            "Mean_Sq_Diff_Weighted",
        ]
    )
    pop_mean = data[resp].mean()
    if not is_continuous(data, pred):
        for i, val in enumerate(data[pred].unique()):
            bin_mean = data[resp][data[pred] == val].mean()
            bin_pop = len(data[resp][data[pred] == val])
            pop_prop = bin_pop / len(data[resp])
            mean_sq_diff = (pop_mean - bin_mean) ** 2
            mean_sq_diff_w = mean_sq_diff * pop_prop
            df.loc[i] = [
                val,
                bin_pop,
                bin_mean,
                pop_mean,
                pop_prop,
                mean_sq_diff,
                mean_sq_diff_w,
            ]
    else:
        data_sorted = data.sort_values(pred)
        data_sorted["bins"] = pd.cut(data_sorted[pred], 10)
        for i, cur_bin in enumerate(data_sorted["bins"].unique()):
            bin_mean = data_sorted[resp][data_sorted["bins"] == cur_bin].mean()
            bin_pop = len(data_sorted[pred][data_sorted["bins"] == cur_bin])
            pop_prop = bin_pop / len(data_sorted[pred])
            mean_sq_diff = (pop_mean - bin_mean) ** 2
            mean_sq_diff_w = mean_sq_diff * pop_prop
            df.loc[i] = [
                i,
                bin_pop,
                bin_mean,
                pop_mean,
                pop_prop,
                mean_sq_diff,
                mean_sq_diff_w,
            ]

    return df, sum(df["Mean_Sq_Diff_Weighted"])


def plot_mean_diff(df, pred):

    fig = px.bar(x=df["(i)"], y=df["Bin_Mean"])
    fig.add_hline(y=df["Pop_Mean"][0])
    fig.update_layout(
        title=f"Mean Difference of Response for {pred}",
        xaxis_title="Bin",
        yaxis_title="Bin Mean",
    )

    file = f"plots/{pred}_mean_diff.html"
    # fig.show()
    fig.write_html(
        file=f"plots/{pred}_mean_diff.html",
        include_plotlyjs="cdn",
    )
    return file


def main():
    db_user = "root"
    db_pass = input("Please enter password: ")  # pragma: allowlist secret
    db_host = "localhost"
    db_database = "baseball"
    connect_string = (
        f"mariadb+mariadbconnector://{db_user}:{db_pass}@{db_host}/{db_database}"
    )

    sql_engine = sqlalchemy.create_engine(connect_string)
    query = """
            SELECT *
            FROM join_team_ba_game
        """
    df = pd.read_sql_query(query, sql_engine)
    pd.set_option("display.max_columns", 20)
    # print(df.head())
    response = "home_team_wins"
    preds_full = list(df.columns[:-1])
    preds = list(
        df.columns[6:-1]
    )  # This is the list of preds that are most useful in predicting the wins

    baseball_cor_table, cor_matrix = cor_calc_cont_cont(df, preds, response)

    # I was able to add the hyper links to the plots but they seem not to click.  Im not sure why,
    # I tested multiple file paths including the full path.
    baseball_cor_table["Predictor 1"] = baseball_cor_table.apply(
        lambda x: '<a href="{}">{}</a>'.format(x["pred1_plot"], x["Predictor 1"]),
        axis=1,
    )
    baseball_cor_table["Predictor 2"] = baseball_cor_table.apply(
        lambda x: '<a href="{}">{}</a>'.format(x["pred2_plot"], x["Predictor 2"]),
        axis=1,
    )
    baseball_cor_table.to_html(
        "./html_files/baseball_cor_table.html", escape=False, render_links=True
    )

    # This is a heatmap of the correlations between the predictors in the baseball dataset.
    fig = ff.create_annotated_heatmap(cor_matrix, preds, preds, showscale=True)
    fig.write_html(
        file="./plots/baseball_cor_matrix.html",
        include_plotlyjs="cdn",
    )
    # fig.show()

    brute_force_metrics = []
    mean_diff_metric_list = []

    for p1 in preds:
        diff_mean_df, mean_diff_metric = mean_diff_tbl(p1, response, df)
        plot_mean_diff(diff_mean_df, p1)
        mean_diff_metric_list.append((mean_diff_metric, p1))
        if is_continuous(df, p1):
            plot_contp_catr(p1, response, df)
        else:
            plot_catp_catr(p1, response, df)

        for p2 in preds:
            calc_matrix, brute_force_metric = brute_force(p1, p2, response, df)
            brute_force_metrics.append((brute_force_metric, p1 + " and " + p2))

            # print(calc_matrix)

    sorted_BFM = sorted(brute_force_metrics, reverse=True)
    print("Brute force Metric Sorted")
    print(np.array(sorted_BFM), "\n")

    sorted_MDM = sorted(mean_diff_metric_list, reverse=True)
    print("Difference of Mean Metric Sorted")
    print(np.array(sorted_MDM), "\n")

    train = df[df["year"] < 2012]
    test = df[df["year"] == 2012]

    log_reg = LogisticRegression().fit(train[preds_full], train[response])
    log_preds = log_reg.predict(test[preds_full])

    print(
        "Logistic prdiction accuracy: ",
        len(test[response][test[response] == log_preds]) / len(test[response]),
    )

    tree_model = DecisionTreeClassifier().fit(train[preds_full], train[response])
    tree_preds = tree_model.predict(test[preds_full])

    print(
        "Tree prdiction accuracy: ",
        len(test[response][test[response] == tree_preds]) / len(test[response]),
    )


if __name__ == "__main__":
    sys.exit(main())
