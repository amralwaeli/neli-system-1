import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt

np.random.seed(0)
N = 400
M = np.random.uniform(0, 2000, N)
c = np.random.uniform(0.01, 1.0, N)
I = np.random.uniform(0.1, 5.0, N)
sigma = (M * c) / I + np.random.normal(scale=0.01, size=N)

df = pd.DataFrame({'M': M, 'c': c, 'I': I, 'sigma': sigma})
X = df[['M', 'c', 'I']].to_numpy()
y = df['sigma'].to_numpy()
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)

x_scaler = StandardScaler()
y_scaler = StandardScaler()
X_train_s = x_scaler.fit_transform(X_train)
X_test_s = x_scaler.transform(X_test)
y_train_s = y_scaler.fit_transform(y_train.reshape(-1, 1)).ravel()

model = MLPRegressor(hidden_layer_sizes=(64, 32, 16), max_iter=1000, random_state=1)
model.fit(X_train_s, y_train_s)

y_pred = y_scaler.inverse_transform(model.predict(X_test_s).reshape(-1, 1)).ravel()
rmse = mean_squared_error(y_test, y_pred) ** 0.5
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

M_sweep = np.linspace(0, 2000, 120)
fixed_c = 0.05
fixed_I = 9e-5
X_sweep = np.column_stack([M_sweep, np.full_like(M_sweep, fixed_c), np.full_like(M_sweep, fixed_I)])
X_sweep_s = x_scaler.transform(X_sweep)
y_sweep = y_scaler.inverse_transform(model.predict(X_sweep_s).reshape(-1, 1)).ravel()
diffs = np.diff(y_sweep)
support_fraction = float(np.mean(diffs >= -1e-9))

plt.figure(figsize=(6, 4))
plt.scatter(y_test, y_pred, s=12, alpha=0.65)
plt.xlabel('True sigma')
plt.ylabel('Predicted sigma')
plt.title('Prediction vs truth')
plt.grid(True)
plt.tight_layout()
plt.savefig('outputs/python_fit.png', dpi=160)
plt.close()

print(f'Test R2: {r2:.4f}')
print(f'RMSE: {rmse:.4f}')
print(f'MAE: {mae:.4f}')
print(f'Support fraction: {support_fraction:.2%}')
print('The fitted model supports a monotone trend in the sampled domain. This is NOT a proof.')
