import numpy as np
import pandas as pd
import time
import joblib
from joblib import dump
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MaxAbsScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

re_generate_rf_model = True

if re_generate_rf_model:
    datatrain1_original = pd.read_csv('/home/mmy/comnets/comnetsemu/examples/yuzhe/ethylene_CO_formatted.csv')
    datatrain2_original = pd.read_csv('/home/mmy/comnets/comnetsemu/examples/yuzhe/ethylene_methane_formatted.csv')

    datatrain1 = datatrain1_original.iloc[:, -16:]
    datatrain2 = datatrain2_original.iloc[:, -16:]

    X1 = np.array(datatrain1)
    X2 = np.array(datatrain2)
    datatrain_array = np.vstack([X1, X2])

    y1 = np.zeros(len(X1))
    y2 = np.ones(len(X2))
    ytrain = np.concatenate([y1, y2])

    max_abs_scaler = MaxAbsScaler()
    xtrain = max_abs_scaler.fit_transform(datatrain_array)

    X_train, X_test, y_train, y_test = train_test_split(xtrain, ytrain, test_size=0.2, random_state=1)

    X_test_df = pd.DataFrame(X_test)
    y_test_df = pd.DataFrame(y_test, columns=['label'])

    test_data_df = pd.concat([X_test_df, y_test_df], axis=1)

    csv_file_path = '/home/mmy/comnets/comnetsemu/examples/yuzhe/test_data_rf.csv'
    test_data_df.to_csv(csv_file_path, index=False)

    print(f"test data saved to {csv_file_path}.")

    # RF model
    clf = RandomForestClassifier(n_estimators=18, max_depth=4, random_state=0)
    random_forest_model = clf.fit(X_train, y_train)

    # save model
    model_filename = 'rf_model.joblib'
    dump(random_forest_model, model_filename)
    print(f"model saved to {model_filename}.")

    # # split the model into 4 subsets
    # for i in range(4):
    #     # 从原始模型中提取一部分树
    #     subset_estimators = random_forest_model.estimators_[i*8:(i+1)*8]
    #     # 创建一个新的随机森林模型，仅包含这部分树
    #     subset_model = RandomForestClassifier(n_estimators=4, max_depth=4, random_state=0)
    #     subset_model.estimators_ = subset_estimators
    #     subset_model.n_classes_ = random_forest_model.n_classes_
    #     subset_model.n_outputs_ = random_forest_model.n_outputs_
    #     subset_model.classes_ = random_forest_model.classes_

    #     # save subset model
    #     model_filename = f'rf_model_subset_{i}.joblib'
    #     joblib.dump(subset_model, model_filename)
    #     print(f"subset model {i} saved to {model_filename}.")

    # 假设 random_forest_model 是已经训练好的原始随机森林模型
    total_trees = len(random_forest_model.estimators_)
    trees_per_subset = total_trees // 3  # 整除，得到每个子集的树的基本数量

    for i in range(3):
        # 计算当前子集应该从哪里开始，到哪里结束
        start = i * trees_per_subset
        # 如果是最后一个子集，包含所有剩余的树
        if i == 2:
            end = total_trees
        else:
            end = start + trees_per_subset
        
        subset_estimators = random_forest_model.estimators_[start:end]
        subset_model = RandomForestClassifier(n_estimators=len(subset_estimators))
        subset_model.estimators_ = subset_estimators
        subset_model.n_classes_ = random_forest_model.n_classes_
        subset_model.n_outputs_ = random_forest_model.n_outputs_
        subset_model.classes_ = random_forest_model.classes_

        # 由于直接修改estimators_列表并不是一个官方支持的方法，这里可能需要进行额外的步骤来确保子模型能正常工作，
        # 比如可能需要手动设置其他必要的属性或者采用不同的方法来创建子模型。

        # 保存子模型
        model_filename = f'rf_model_subset_{i}.joblib'
        joblib.dump(subset_model, model_filename)
        print(f"Subset model {i} saved to {model_filename}.")


start_time = time.time()

# load test data
# /home/mmy/comnets/comnetsemu/examples/yuzhe/client_svm_1_method.py
datatrain_original = pd.read_csv('/home/mmy/comnets/comnetsemu/examples/yuzhe/test_data_rf.csv')
datatrain = datatrain_original.iloc[:, : 16]

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

# prediction fuction
y_pred = random_forest_model.predict(x_test)
# y_pred =random.predict(X_test)

# print('ground truth           :',y_test)
cross_val_acc = cross_val_score(random_forest_model, x_test, y_test, cv=5).mean() * 100
print('cross validation accuracy   : {}%'.format(cross_val_acc))

end_time = time.time()
print("runing time of prediction part:", end_time - start_time, "s")