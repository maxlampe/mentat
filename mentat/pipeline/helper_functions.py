
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import krippendorff

from mentat.config import config_params
from mentat.pipeline import preference_tools, bootstrap_tools

# Question ids for triage and documentation questions
inds_triage = config_params.inds_triage
inds_documentation = config_params.inds_documentation
# Color rubric for question categories for consistent plots
cols = config_params.cols


def import_raw_annotations(directory: str):
    dataframes = []
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            file_path = os.path.join(directory, filename)
            df = pd.read_csv(file_path)
            
            # Get annotator information
            rater_id = df.loc[1, 'rater_id'].lower()
            participant_name = df.loc[1, 'participant_name'].lower()
            
            # Remove first four lines and last one
            df = df.iloc[4:-1].reset_index(drop=True)
            # print(rater_id, participant_name)
            df['rater_id'] = rater_id
            df['participant_name'] = participant_name
            dataframes.append(df)

    raw_data = pd.concat(dataframes)

    return raw_data


def annotation_data_check(input_data: pd.DataFrame):
    """"""

    assert np.unique(input_data["q_no"]).shape[-1] == 61, "Some questions not annotated."
    hist_plot = plt.hist(input_data["q_no"], bins=440)
    count_min = np.unique(hist_plot[0])[1]
    print(f"Minimum number of answers: {count_min}")


def process_raw_data_annotations(input_data: pd.DataFrame):
    """Processing data"""

    annotator_individual_data = {}
    # Key = Quesiton ID
    response_data = {key: [] for key in range(1, 220)}
    for resp_i, resp in enumerate(input_data["response"]):
        loaded_dict = json.loads(resp)
        cmt = loaded_dict["comment"]
        # print(resp_i, loaded_dict)
        
        # Reverse randomization of answer options
        q_order = json.loads(input_data["question_order"].to_numpy()[resp_i])
        # print("order ", q_order, type(q_order))
        a = np.array(
            [
                loaded_dict["Q0"],
                loaded_dict["Q1"],
                loaded_dict["Q2"],
                loaded_dict["Q3"],
                loaded_dict["Q4"],
            ]
        )
        # print("a (unordered) ", a, type(a))
        a = a[q_order]
        # print("a (  ordered) ", a, type(a))
        
        q_no = input_data["q_no"].to_numpy()[resp_i]
        rater_id = input_data["rater_id"].to_numpy()[resp_i]
        q_key = input_data["q_key"].to_numpy()[resp_i]
        q = input_data["q"].to_numpy()[resp_i]
        
        try:
            annotator_individual_data[rater_id].append(a)
        except KeyError:
            annotator_individual_data[rater_id] = []
            annotator_individual_data[rater_id].append(a)
        
        response_data[q_no].append(a)
        # Going through comments to check for flaws in questions or other issues
        if loaded_dict["comment"] != "":
            # print(raw_data["q_no"][resp_i])
            # print(rater_id, q_no, q_key, cmt)
            pass
        
        # Optional rescaling or binning of annotation values (Don't use!)
        if 0:
            # Bin response entries
            # bin_edges = np.array([0, 20, 40, 60, 80, 101])
            bin_edges = np.array([0, 33.3333, 66.6666, 100.0001])
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            # bin_centers = np.array([0, 100])

            # response_data = {key: [bin_centers[(np.digitize(vals, bin_edges, right=False)) - 1] for vals in value] for key, value in response_data.items()}
            response_data = {
                key: [100. / (1 + np.exp(-(vals - 50) * 0.99)) for vals in value] 
                for key, value in response_data.items()
            }

    return response_data, annotator_individual_data


# ----------
# Helper functions to be used as input operators for bootstrapping wrapper
# ----------
def calc_mean(data):
    """"""
    return np.mean(data, axis=0)

def calc_alpha(data):
    """"""
    return krippendorff.alpha(
        reliability_data=data, level_of_measurement='interval'
    )

def calc_bt_scores(data):
    """"""

    pairwise_data = preference_tools.pairwise_wins(data)
    bt7274 = preference_tools.BradleyTerry(data=pairwise_data, k=data.shape[-1])

    return bt7274.return_probs()


# ----------
# High-level analysis functions to called in scripts
# ----------
def calc_mean_and_alphas(input_data: pd.DataFrame, do_boot: bool = False):
    """"""

    res_dict = {}

    for k in input_data:
        res = input_data[k]
        if res != [] and (k in inds_documentation or k in inds_triage):
            res = np.array(res)
            
            res_mean = bootstrap_tools.bootstrap_wrap(res, calc_mean, n_boot=1000)
            res_alpha = bootstrap_tools.bootstrap_wrap(
                res, calc_alpha, n_boot=1000, out_dim=0
            )

            if do_boot:
                boot_res_mean = bootstrap_tools.bootstrap_wrap(res, calc_mean, n_boot=1000)
                boot_res_alpha = bootstrap_tools.bootstrap_wrap(
                    res, calc_alpha, n_boot=1000, out_dim=0
                )
            else:
                res_mean = calc_mean(res)
                boot_res_mean = {
                    "result": res_mean,
                    "ci_lower": res_mean,
                    "ci_upper": res_mean,
                }
                res_alpha = calc_alpha(res)
                boot_res_alpha = {
                    "result": res_alpha,
                    "ci_lower": res_alpha,
                    "ci_upper": res_alpha,
                }

            res_dict[k] = {
                "res": boot_res_mean["result"],
                "ci_lower": boot_res_mean["ci_lower"],
                "ci_upper": boot_res_mean["ci_upper"],
                "alpha": boot_res_alpha["result"],
                "ci_alpha_lower": boot_res_alpha["ci_lower"],
                "ci_alpha_upper": boot_res_alpha["ci_upper"],
            }

    return res_dict


def calc_preference_probs(input_data: pd.DataFrame, do_boot: bool = False):
    """"""

    res_dict = {}
    for k in input_data:
        res = input_data[k]
        if res != [] and (k in inds_documentation or k in inds_triage):
            res = np.array(res)

            if do_boot:
                boot_res = bootstrap_tools.bootstrap_wrap(res, calc_bt_scores, 25)
            else:
                bt_scores = calc_bt_scores(res)
                boot_res = {
                    "result": bt_scores,
                    "ci_lower": bt_scores,
                    "ci_upper": bt_scores,
                }

            res_dict[k] = {
                "bt_scores": boot_res["result"],
                "ci_lower": boot_res["ci_lower"],
                "ci_upper": boot_res["ci_upper"],
            }
    return res_dict