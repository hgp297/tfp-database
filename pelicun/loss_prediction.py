############################################################################
#               ML prediction models for isolator loss data

# Created by:   Huy Pham
#               University of California, Berkeley

# Date created: December 2022

# Description:  ML models

# Open issues:  (1) 

############################################################################

import pandas as pd
import numpy as np
idx = pd.IndexSlice
pd.options.display.max_rows = 30

# temporary spyder debugger error hack
import collections
collections.Callable = collections.abc.Callable

#%% concat with other data
loss_data = pd.read_csv('./results/loss_estimate_data.csv', index_col=None)
full_isolation_data = pd.read_csv('full_isolation_data.csv', index_col=None)

df = pd.concat([full_isolation_data, loss_data], axis=1)
# df['max_drift'] = df[["driftMax1", "driftMax2", "driftMax3"]].max(axis=1)
# df['max_accel'] = df[["accMax0", "accMax1", "accMax2", "accMax3"]].max(axis=1)
# df['max_vel'] = df[["velMax0", "velMax1", "velMax2", "velMax3"]].max(axis=1)
#%% new class
class Prediction:
    
    # sets up the problem by grabbing the x covariates
    def __init__(self, data):
        self._raw_data = data
        self.k = len(data)
        self.X = data[['gapRatio', 'RI', 'zetaM', 'Tm']]
        
    # sets up prediction variable
    def set_outcome(self, outcome_var):
        self.y = self._raw_data[[outcome_var]]
        
    # if classification is done, plot the predictions
    def plot_classification(self):
        import matplotlib.pyplot as plt
        
        xx = self.xx
        yy = self.yy
        Z = self.svc.decision_function(self.X_plot)
        Z = Z.reshape(xx.shape)
        
        plt.imshow(
            Z,
            interpolation="nearest",
            extent=(xx.min(), xx.max(),
                    yy.min(), yy.max()),
            aspect="auto",
            origin="lower",
            cmap=plt.cm.PuOr_r,
        )
            
        plt_density = 100
        
        plt.contour(xx, yy, Z, levels=[0], linewidths=2, linestyles="dashed")
        plt.scatter(self.X_train['gapRatio'][:plt_density],
                    self.X_train['RI'][:plt_density],
                    s=30, c=self.y_train[:plt_density],
                    cmap=plt.cm.Paired, edgecolors="k")
        plt.xlabel('Gap ratio')
        plt.ylabel('Ry')
        plt.title('Impact classification')
        plt.show()
        
    # make a generalized 2D plotting grid, defaulted to gap and Ry
    # grid is based on the bounds of input data
    def make_2D_plotting_space(self, res, x_var='gapRatio', y_var='RI'):
        xx, yy = np.meshgrid(np.linspace(min(self.X[x_var]),
                                         max(self.X[x_var]),
                                         res),
                             np.linspace(min(self.X[y_var]),
                                         max(self.X[y_var]),
                                         res))

        if (x_var=='gapRatio') and (y_var=='RI'):
            third_var = 'zetaM'
            fourth_var = 'Tm'
           
        self.xx = xx
        self.yy = yy
        self.X_plot = pd.DataFrame({x_var:xx.ravel(),
                             y_var:yy.ravel(),
                             third_var:np.repeat(self.X[third_var].median(),
                                                 res*res),
                             fourth_var:np.repeat(self.X[fourth_var].median(), 
                                                  res*res)})
                             
        return(self.X_plot)
        
    # TODO: consider method that cleans data based on prediction outcome
        
    # train test split to be done before any learning 
    def test_train_split(self, percentage):
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(self.X, self.y, 
                                                            test_size=percentage,
                                                            random_state=985)
        
        from numpy import ravel
        
        self.X_train = X_train
        self.X_test = X_test
        self.y_train = ravel(y_train)
        self.y_test = ravel(y_test)
        
    # Train SVM regression
    def fit_svr(self):
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVR
        from sklearn.model_selection import GridSearchCV
        
        # pipeline to scale -> SVR
        sv_pipe = Pipeline([('scaler', StandardScaler()),
                            ('svr', SVR(kernel='rbf'))])
        
        # cross-validate several parameters
        parameters = [
            {'svr__C':[1.0, 10.0, 100.0, 1000.0, 10000.0, 100000.0],
             'svr__epsilon':[0.01, 0.1, 1.0],
             'svr__gamma':np.logspace(-2, 2, 3)}
            ]
        
        svr_cv = GridSearchCV(sv_pipe, param_grid=parameters)
        svr_cv.fit(self.X_train, self.y_train)
        
        print("The best parameters are %s"
              % (svr_cv.best_params_))
        
        # set pipeline to use CV params
        sv_pipe.set_params(**svr_cv.best_params_)
        sv_pipe.fit(self.X_train, self.y_train)
        
        self.svr = sv_pipe
     
    # Train SVM classification
    def fit_svc(self, neg_wt=1.0):
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
        from sklearn.model_selection import GridSearchCV
        
        # pipeline to scale -> SVC
        wts = {0: neg_wt, 1:1.0}
        sv_pipe = Pipeline([('scaler', StandardScaler()),
                            ('svc', SVC(kernel='rbf', gamma='auto',
                                        probability=True,
                                        class_weight=wts))])
        
        # cross-validate several parameters
        parameters = [
            {'svc__C':[0.1, 1.0, 10.0, 100.0, 1000.0]}
            ]
        
        svc_cv = GridSearchCV(sv_pipe, param_grid=parameters)
        svc_cv.fit(self.X_train, self.y_train)
        
        # set pipeline to use CV params
        sv_pipe.set_params(**svc_cv.best_params_)
        sv_pipe.fit(self.X_train, self.y_train)
        
        print("The best parameters are %s with a score of %0.2f"
              % (svc_cv.best_params_, svc_cv.best_score_))
        
        self.svc = sv_pipe
        
    # TODO: if params passed, don't do CV
    
    # Train kernel ridge regression
    def fit_kernel_ridge(self, kernel_name='rbf'):
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.kernel_ridge import KernelRidge
        from sklearn.model_selection import GridSearchCV
        
        kr_pipe = Pipeline([('scaler', StandardScaler()),
                             ('kr', KernelRidge(kernel=kernel_name))])
        
        # cross-validate several parameters
        parameters = [
            {'kr__alpha':[0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0],
             'kr__gamma':np.logspace(-2, 2, 5)}
            ]
        
        kr_cv = GridSearchCV(kr_pipe, param_grid=parameters)
        kr_cv.fit(self.X_train, self.y_train)
        
        # set pipeline to use CV params
        print("The best parameters are %s"
              % (kr_cv.best_params_))
        kr_pipe.set_params(**kr_cv.best_params_)
        kr_pipe.fit(self.X_train, self.y_train)
        
        self.kr = kr_pipe
        
    # Train regular ridge regression
    def fit_ols_ridge(self):
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import RidgeCV
        
        or_pipe = Pipeline([('scaler', StandardScaler()),
                             ('o_ridge', RidgeCV(alphas=np.logspace(-2, 2, 5)))]
            )
        
        or_pipe.fit(self.X_train, self.y_train)
        
        self.o_ridge = or_pipe
        
    # assumes that problem is already created
    def predict_loss(self, impact_pred_mdl, hit_loss_mdl, miss_loss_mdl):
        # get points that are predicted impact from full dataset
        preds_imp = impact_pred_mdl.svc.predict(self.X)
        df_imp = self.X[preds_imp == 1]
        
        # run SVR_hit model on this dataset
        loss_pred_hit = pd.DataFrame(
                {'median_loss_pred':
                    hit_loss_mdl.svr.predict(df_imp)},
                    index=df_imp.index)
                
        
        # get points that are predicted no impact from full dataset
        df_mss = self.X[preds_imp == 0]
        
        # run SVR_miss model on this dataset
        loss_pred_miss = pd.DataFrame(
                {'median_loss_pred':
                    miss_loss_mdl.svr.predict(df_mss)},
                    index=df_mss.index)
            
        self.median_loss_pred = pd.concat([loss_pred_hit,loss_pred_miss], 
                                          axis=0).sort_index(ascending=True)
        
    # TODO: GP Regression model
 
# make prediction objects for impacted and non-impacted datasets
df_hit = df[df['impacted'] == 1]
mdl_hit = Prediction(df_hit)
mdl_hit.set_outcome('cost_50%')
mdl_hit.test_train_split(0.2)

df_miss = df[df['impacted'] == 0]
mdl_miss = Prediction(df_miss)
mdl_miss.set_outcome('cost_50%')
mdl_miss.test_train_split(0.2)

#%% fit impact
# prepare the problem
mdl = Prediction(df)
mdl.set_outcome('impacted')
mdl.test_train_split(0.2)

# fit SVM classification for impact
mdl.fit_svc(neg_wt=0.6)

# predict the entire dataset
preds_imp = mdl.svc.predict(mdl.X)
probs_imp = mdl.svc.predict_proba(mdl.X)

# we've done manual CV to pick the hyperparams that trades some accuracy
# in order to lower false negatives
from sklearn.metrics import confusion_matrix

tn, fp, fn, tp = confusion_matrix(mdl.y, preds_imp).ravel()
print('False negatives: ', fn)
print('False positives: ', fp)

# make grid and plot classification predictions
X_plot = mdl.make_2D_plotting_space(100)
mdl.plot_classification()

#%% Fit costs (SVR)

# fit impacted set
mdl_hit.fit_svr()
cost_pred_hit = mdl_hit.svr.predict(mdl_hit.X_test)
comparison_cost_hit = np.array([mdl_hit.y_test, 
                                      cost_pred_hit]).transpose()
        
# fit no impact set
mdl_miss.fit_svr()
cost_pred_miss = mdl_miss.svr.predict(mdl_miss.X_test)
comparison_cost_miss = np.array([mdl_miss.y_test, 
                                      cost_pred_miss]).transpose()
        
scr = mdl_miss.svr.score(mdl_miss.X_test, mdl_miss.y_test)

import matplotlib.pyplot as plt
mdl_miss.make_2D_plotting_space(100)

xx = mdl_miss.xx
yy = mdl_miss.yy
Z = mdl_miss.svr.predict(mdl_miss.X_plot)
Z = Z.reshape(xx.shape)

fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
# Plot the surface.
surf = ax.plot_surface(xx, yy, Z, cmap=plt.cm.coolwarm,
                       linewidth=0, antialiased=False)

ax.scatter(df_miss['gapRatio'], df_miss['RI'], df_miss['cost_50%'],
           edgecolors='k')

ax.set_xlabel('Gap ratio')
ax.set_ylabel('Ry')
ax.set_zlabel('Median loss ($)')
ax.set_title('Median cost predictions given no impact (SVR)')
ax.set_zlim([0, 1e5])
plt.show()

#%% Fit costs (kernel ridge)
kernel_type = 'polynomial'

# fit impacted set
mdl_hit.fit_kernel_ridge(kernel_name=kernel_type)
cost_pred_hit = mdl_hit.kr.predict(mdl_hit.X_test)
comparison_cost_hit = np.array([mdl_hit.y_test, 
                                      cost_pred_hit]).transpose()
        
# fit no impact set
mdl_miss.fit_kernel_ridge(kernel_name=kernel_type)
cost_pred_miss = mdl_miss.kr.predict(mdl_miss.X_test)
comparison_cost_miss = np.array([mdl_miss.y_test, 
                                      cost_pred_miss]).transpose()
        
scr = mdl_miss.kr.score(mdl_miss.X_test, mdl_miss.y_test)

import matplotlib.pyplot as plt
mdl_miss.make_2D_plotting_space(100)

xx = mdl_miss.xx
yy = mdl_miss.yy
Z = mdl_miss.kr.predict(mdl_miss.X_plot)
Z = Z.reshape(xx.shape)

fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
# Plot the surface.
surf = ax.plot_surface(xx, yy, Z, cmap=plt.cm.coolwarm,
                       linewidth=0, antialiased=False)

ax.scatter(df_miss['gapRatio'], df_miss['RI'], df_miss['cost_50%'],
           edgecolors='k')

ax.set_xlabel('Gap ratio')
ax.set_ylabel('Ry')
ax.set_zlabel('Median loss ($)')
ax.set_title('Median cost predictions given no impact (Polynomial kernel ridge)')
ax.set_zlim([0, 1e6])
plt.show()

#%% Fit costs (regular ridge)

# sensitive to alpha. keep alpha > 1e-2 since smaller alphas will result in 
# flat line to minimize the outliers' error

# results in a fit similar to kernel ridge

# fit impacted set
mdl_hit.fit_ols_ridge()
cost_pred_hit = mdl_hit.o_ridge.predict(mdl_hit.X_test)
comparison_cost_hit = np.array([mdl_hit.y_test, 
                                      cost_pred_hit]).transpose()
        
# fit no impact set
mdl_miss.fit_ols_ridge()
cost_pred_miss = mdl_miss.o_ridge.predict(mdl_miss.X_test)
comparison_cost_miss = np.array([mdl_miss.y_test, 
                                      cost_pred_miss]).transpose()
        
scr = mdl_miss.o_ridge.score(mdl_miss.X_test, mdl_miss.y_test)

#%% aggregate the two models
mdl_imp_clf = mdl
mdl.predict_loss(mdl_imp_clf, mdl_hit, mdl_miss)
comparison_cost = np.array([df['cost_50%'],
                            np.ravel(mdl.median_loss_pred)]).transpose()

#%% Big cost prediction plot

import matplotlib.pyplot as plt
X_plot = mdl.make_2D_plotting_space(100)

grid_mdl = Prediction(X_plot)
grid_mdl.predict_loss(mdl_imp_clf, mdl_hit, mdl_miss)
grid_mdl.make_2D_plotting_space(100)

xx = grid_mdl.xx
yy = grid_mdl.yy
Z = np.array(grid_mdl.median_loss_pred)
Z = Z.reshape(xx.shape)

fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
# Plot the surface.
surf = ax.plot_surface(xx, yy, Z, cmap=plt.cm.coolwarm,
                       linewidth=0, antialiased=False)

ax.scatter(df['gapRatio'], df['RI'], df['cost_50%'],
           edgecolors='k')

ax.set_xlabel('Gap ratio')
ax.set_ylabel('Ry')
ax.set_zlabel('Median loss ($)')
ax.set_title('Median cost predictions: SVC-impact, SVR-loss')
plt.show()

#%% Fit costs (SVR, across all data)

# fit impacted set
mdl = Prediction(df)
mdl.set_outcome('cost_50%')
mdl.test_train_split(0.2)
mdl.fit_svr()

X_plot = mdl.make_2D_plotting_space(100)
import matplotlib.pyplot as plt

xx = mdl.xx
yy = mdl.yy
Z = mdl.svr.predict(mdl.X_plot)
Z = Z.reshape(xx.shape)

fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
# Plot the surface.
surf = ax.plot_surface(xx, yy, Z, cmap=plt.cm.coolwarm,
                       linewidth=0, antialiased=False)

ax.scatter(df['gapRatio'], df['RI'], df['cost_50%'],
           edgecolors='k')

ax.set_xlabel('Gap ratio')
ax.set_ylabel('Ry')
ax.set_zlabel('Median loss ($)')
ax.set_title('Median cost predictions across all data (SVR)')
plt.show()
        

#%% dirty test prediction plots for cost
plt.close('all')
plt.figure()
plt.scatter(mdl_miss.X_test['RI'], mdl_miss.y_test)
plt.scatter(mdl_miss.X_test['RI'], cost_pred_miss)

plt.figure()
plt.scatter(mdl_hit.X_test['RI'], mdl_hit.y_test)
plt.scatter(mdl_hit.X_test['RI'], cost_pred_hit)

#%% Other plotting

# idea for plots

# stats-style qq error plot
# Tm, zeta plots