import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score
from pathlib import Path

df = pd.read_csv('runs/aggregated/dataframe_with_comet.csv')

# Drop rows with parse warnings if conf is missing, or just handle missing conf
df['conf'] = pd.to_numeric(df['conf'], errors='coerce')
df = df.dropna(subset=['conf', 'comet_score'])

models = df['model_id'].unique()
results = []

for m in models:
    sub = df[df['model_id'] == m].copy()
    
    # define low quality by COMET (bottom 20%)
    threshold = sub['comet_score'].quantile(0.20)
    sub['error_comet'] = (sub['comet_score'] <= threshold).astype(int)
    
    if sub['error_comet'].sum() > 0 and sub['error_comet'].sum() < len(sub):
        # We invert conf because higher conf means LOWER probability of error
        auroc = roc_auc_score(sub['error_comet'], 1.0 - sub['conf'])
    else:
        auroc = np.nan
        
    corr = sub['conf'].corr(sub['comet_score'], method='spearman')
    
    results.append({
        'Model': m,
        'Spearman_Conf_vs_COMET': corr,
        'AUROC_Predict_Bad_COMET': auroc,
        'Mean_COMET': sub['comet_score'].mean()
    })

res_df = pd.DataFrame(results)
print(res_df.to_string(index=False))
res_df.to_csv('tables/comet_results.csv', index=False)

# Write a latex table
tex_out = "\\begin{table}[t]\n\\centering\n\\begin{tabular}{lccc}\n\\toprule\n"
tex_out += "Model & Mean COMET & Spearman & AUROC \\\\\n\\midrule\n"
for _, r in res_df.iterrows():
    m = str(r['Model']).replace('_', '\\_')
    tex_out += f"{m} & {r['Mean_COMET']:.3f} & {r['Spearman_Conf_vs_COMET']:.3f} & {r['AUROC_Predict_Bad_COMET']:.3f} \\\\\n"
tex_out += "\\bottomrule\n\\end{tabular}\n\\caption{COMET-based evaluation. Low quality defined as bottom 20\\% COMET within model.}\n\\label{tab:comet}\n\\end{table}\n"

with open('tables/comet_table.tex', 'w') as f:
    f.write(tex_out)

print("Saved latex table to tables/comet_table.tex")
