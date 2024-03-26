import numpy as np
import pandas as pd
import time
import joblib
from scipy.stats import mode

start_time = time.time()

# load test data
# /home/mmy/comnets/comnetsemu/examples/yuzhe/client_svm_1_method.py
datatrain_original = pd.read_csv('/home/mmy/comnets/comnetsemu/examples/yuzhe/test_data_rf.csv', nrows=10)
datatrain = datatrain_original.iloc[:, :16]

X_test = np.array(datatrain)

# generate test feature
x_test = X_test[:, :15]

# generate test label
y_test = datatrain_original.iloc[:, -1]
y_test = np.array(y_test)
y_test = y_test.tolist()

# load rf model after training
with open('rf_model.joblib', 'rb') as file:
    random_forest_model = joblib.load(file)

# 加载子模型
models = [joblib.load(f'rf_model_subset_{i}.joblib') for i in range(3)]

# 假设 X_test 是您要预测的数据
predictions = np.array([model.predict(x_test) for model in models])

print(predictions)
# 计算多数投票的结果
majority_vote = mode(predictions, axis=0)
print(majority_vote)
# 获取多数投票的结果
final_predictions = majority_vote.mode

print(final_predictions)
# 打印最终预测结果
# print("Final predictions:", final_predictions)