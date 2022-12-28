############################################################################
#               Loss estimation of TFP database

# Created by:   Huy Pham
#               University of California, Berkeley

# Date created: December 2022

# Description:  Calling function to predict component damage and loss in the 
# initial database

# Open issues:  (1) 

############################################################################

import pandas as pd
idx = pd.IndexSlice
pd.options.display.max_rows = 30

# and import pelicun classes and methods
from pelicun.base import convert_to_MultiIndex
from estimate_loss import estimate_damage

import warnings
warnings.filterwarnings('ignore')

#%% if files have been unprepared, prepare
import sys
sys.path.append('..')
import tmp_cleaner
from get_demand_data import get_EDP
databasePath = '../sessionOut/'
databaseFile = 'sessionSummary.csv'

# clean data and add additional variables
resultsDf = pd.read_csv(databasePath+databaseFile)
data = tmp_cleaner.cleanDat(resultsDf)
pelicunPath = './pelicun/'
data.to_csv(pelicunPath+'full_isolation_data.csv', index=True)

# write into pelicun style EDP
edp = get_EDP(data)
edp.to_csv(pelicunPath+'demand_data.csv', index=True)

#%% prepare whole set of runs

full_isolation_data = pd.read_csv('full_isolation_data.csv', index_col=0)


# load the component configuration
cmp_marginals = pd.read_csv('cmp_marginals.csv', index_col=0)

# Prepare demand data set to match format
all_demands = pd.read_csv('demand_data.csv', index_col=None,header=None).transpose()

all_demands.columns = all_demands.loc[0]
all_demands = all_demands.iloc[1:, :]
all_demands.columns = all_demands.columns.fillna('EDP')

all_demands = all_demands.set_index('EDP', drop=True)

# run_idx = 45
# #run_idx = 324
# raw_demands = all_demands[['Units', str(run_idx)]]
# raw_demands.columns = ['Units', 'Value']
# raw_demands = convert_to_MultiIndex(raw_demands, axis=0)
# raw_demands.index.names = ['type','loc','dir']

# run_data = full_isolation_data.loc[run_idx]

#%% estimate loss for set

all_losses = []
loss_cmp_group = []
col_list = []
irr_list = []

# for run_idx in range(3):
for run_idx in full_isolation_data.index:
    run_data = full_isolation_data.loc[run_idx]
    
    raw_demands = all_demands[['Units', str(run_idx)]]
    raw_demands.columns = ['Units', 'Value']
    raw_demands = convert_to_MultiIndex(raw_demands, axis=0)
    raw_demands.index.names = ['type','loc','dir']
    
    print('========================================')
    print('Estimating loss for run index', run_idx)
    
    [cmp, dmg, loss, loss_cmp, agg, 
         collapse_rate, irr_rate] = estimate_damage(raw_demands,
                                                run_data,
                                                cmp_marginals)
    loss_summary = agg.describe([0.1, 0.5, 0.9])
    cost = loss_summary['repair_cost']['mean']
    time_l = loss_summary[('repair_time', 'parallel')]['mean']
    time_u = loss_summary[('repair_time', 'sequential')]['mean']
    
    print('Mean repair cost: ', f'${cost:,.2f}')
    print('Mean lower bound repair time: ', f'{time_l:,.2f}', 'worker-days')
    print('Mean upper bound repair time: ', f'{time_u:,.2f}', 'worker-days')
    print('Collapse frequency: ', f'{collapse_rate:.2%}')
    print('Irreparable RID frequency: ', f'{irr_rate:.2%}')
    print('Replacement frequency: ', f'{collapse_rate+irr_rate:.2%}')
    all_losses.append(loss_summary)
    loss_cmp_group.append(loss_cmp)
    col_list.append(collapse_rate)
    irr_list.append(irr_rate)
    
loss_file = './results/loss_estimate_data.csv'
by_cmp_file = './results/loss_estimate_by_groups.csv'
pd.concat(all_losses).to_csv(loss_file)
pd.concat(loss_cmp_group).to_csv(by_cmp_file)

#%% flatten data

loss_df = pd.read_csv(loss_file, header=[0,1])

loss_header = ['cost_mean', 'cost_std', 'cost_min',
               'cost_10%', 'cost_50%', 'cost_90%', 'cost_max',
               'time_l_mean', 'time_l_std', 'time_l_min',
               'time_l_10%', 'time_l_50%', 'time_l_90%', 'time_l_max',
               'time_u_mean', 'time_u_std', 'time_u_min',
               'time_u_10%', 'time_u_50%', 'time_u_90%', 'time_u_max']

all_rows = []

for row_idx in range(len(loss_df)):
    if row_idx % 8 == 0:
        # get the block with current run, drop the 'Count'
        run_df = loss_df[row_idx:row_idx+8]
        run_df = run_df.transpose()
        run_df.columns = run_df.iloc[0]
        run_df = run_df.drop(run_df.index[0])
        new_row = pd.concat([run_df.iloc[0], run_df.iloc[1], run_df.iloc[2]])
        new_row = new_row.drop(new_row.index[0])
        
        all_rows.append(new_row)
        
loss_df_data = pd.concat(all_rows, axis=1).T
loss_df_data.columns = loss_header

loss_df_data['collapse_freq'] = col_list
loss_df_data['irreparable_freq'] = irr_list
loss_df_data['replacement_freq'] = [x + y for x, y in zip(col_list, irr_list)]

# loss_df_data.to_csv(loss_file, index=False)
#%%
group_df = pd.read_csv(by_cmp_file, header=0)
group_header = ['B_mean', 'B_std', 'B_min',
               'B_25%', 'B_50%', 'B_75%', 'B_max',
               'C_mean', 'C_std', 'C_min',
               'C_25%', 'C_50%', 'C_75%', 'C_max',
               'D_mean', 'D_std', 'D_min',
               'D_25%', 'D_50%', 'D_75%', 'D_max',
               'E_mean', 'E_std', 'E_min',
               'E_25%', 'E_50%', 'E_75%', 'E_max']

all_rows = []

for row_idx in range(len(group_df)):
    if row_idx % 8 == 0:
        # get the block with current run, drop the 'Count'
        run_df = group_df[row_idx:row_idx+8]
        run_df = run_df.transpose()
        run_df.columns = run_df.iloc[0]
        run_df = run_df.drop(run_df.index[0])
        new_row = pd.concat([run_df.iloc[0], run_df.iloc[1], run_df.iloc[2], run_df.iloc[3]])
        new_row = new_row.drop(new_row.index[0])
        
        all_rows.append(new_row)
        
group_df_data = pd.concat(all_rows, axis=1).T
group_df_data.columns = group_header

all_data = pd.concat([loss_df_data, group_df_data], axis=1)
all_data.to_csv(loss_file, index=False)