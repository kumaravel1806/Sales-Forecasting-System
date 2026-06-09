import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from pmdarima import auto_arima
import warnings
warnings.filterwarnings('ignore')

class HistoricalSalesAnalyzer:
    def __init__(self, file_path):
        """
        Initialize the analyzer with the path to the sales data file.
        Supports CSV, Excel, and Parquet formats.
        """
        self.file_path = file_path
        self.df = None
        self.sales_ts = None
        self.forecast_periods = 12  # Default forecast periods
        
    def load_data(self):
        """Load and preprocess the sales data."""
        try:
            if self.file_path.endswith('.csv'):
                self.df = pd.read_csv(self.file_path)
            elif self.file_path.endswith(('.xls', '.xlsx')):
                self.df = pd.read_excel(self.file_path)
            elif self.file_path.endswith('.parquet'):
                self.df = pd.read_parquet(self.file_path)
            else:
                raise ValueError("Unsupported file format. Please use CSV, Excel, or Parquet.")
                
            print("Data loaded successfully!")
            print(f"Data shape: {self.df.shape}")
            print("\nFirst few rows:")
            print(self.df.head())
            
            # Auto-detect date and value columns
            self.detect_columns()
            
            # Convert date column to datetime
            self.df[self.date_col] = pd.to_datetime(self.df[self.date_col], errors='coerce')
            
            # Set date as index and sort
            self.df = self.df.set_index(self.date_col).sort_index()
            
            # Resample to daily frequency if needed
            self.sales_ts = self.df[self.value_col].resample('D').sum()
            
            return True
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False
    
    def detect_columns(self):
        """Automatically detect date and value columns."""
        # Try to find date column
        date_candidates = ['date', 'Date', 'DATE', 'timestamp', 'time', 'Time', 'sale_date', 'order_date']
        self.date_col = next((col for col in self.df.columns if col.lower() in [x.lower() for x in date_candidates]), 
                            self.df.select_dtypes(include=['datetime', 'datetime64']).columns[0] if not self.df.select_dtypes(include=['datetime', 'datetime64']).empty else self.df.columns[0])
        
        # Try to find value column
        value_candidates = ['sales', 'amount', 'value', 'revenue', 'quantity']
        self.value_col = next((col for col in self.df.columns if col.lower() in [x.lower() for x in value_candidates]),
                             self.df.select_dtypes(include=['int64', 'float64']).columns[0])
        
        print(f"Detected date column: {self.date_col}")
        print(f"Detected value column: {self.value_col}")
    
    def plot_sales_trend(self):
        """Plot the sales trend over time."""
        plt.figure(figsize=(14, 6))
        self.sales_ts.plot(title='Historical Sales Trend', color='blue')
        plt.xlabel('Date')
        plt.ylabel('Sales')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('sales_trend.png')
        plt.close()
        
    def plot_moving_averages(self, windows=[7, 30, 90]):
        """Plot moving averages for different window sizes."""
        plt.figure(figsize=(14, 6))
        self.sales_ts.plot(label='Original', alpha=0.5)
        
        for window in windows:
            self.sales_ts.rolling(window=window).mean().plot(
                label=f'{window}-day Moving Avg')
                
        plt.title('Sales with Moving Averages')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('moving_averages.png')
        plt.close()
    
    def seasonal_decomposition(self, period=30):
        """Perform and plot seasonal decomposition."""
        result = seasonal_decompose(self.sales_ts, period=period, extrapolate_trend='freq')
        
        plt.figure(figsize=(14, 10))
        
        plt.subplot(411)
        result.observed.plot(ax=plt.gca())
        plt.title('Observed')
        
        plt.subplot(412)
        result.trend.plot(ax=plt.gca())
        plt.title('Trend')
        
        plt.subplot(413)
        result.seasonal.plot(ax=plt.gca())
        plt.title('Seasonal')
        
        plt.subplot(414)
        result.resid.plot(ax=plt.gca())
        plt.title('Residual')
        
        plt.tight_layout()
        plt.savefig('seasonal_decomposition.png')
        plt.close()
    
    def test_stationarity(self):
        """Perform Augmented Dickey-Fuller test for stationarity."""
        result = adfuller(self.sales_ts.dropna())
        
        print('\nADF Statistic:', result[0])
        print('p-value:', result[1])
        print('Critical Values:')
        for key, value in result[4].items():
            print(f'   {key}: {value:.3f}')
        
        if result[1] <= 0.05:
            print("\nThe time series is stationary (p-value <= 0.05)")
        else:
            print("\nThe time series is not stationary (p-value > 0.05)")
    
    def plot_acf_pacf(self):
        """Plot ACF and PACF for ARIMA parameter selection."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
        plot_acf(self.sales_ts, lags=40, ax=ax1)
        plot_pacf(self.sales_ts, lags=40, ax=ax2, method='ywm')
        plt.tight_layout()
        plt.savefig('acf_pacf.png')
        plt.close()
    
    def build_arima_model(self):
        """Build and fit ARIMA model with automatic parameter selection."""
        print("\nSearching for best ARIMA parameters...")
        stepwise_fit = auto_arima(
            self.sales_ts, 
            seasonal=True, 
            m=12,  # Monthly seasonality
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore"
        )
        
        print("Best ARIMA parameters:", stepwise_fit.order)
        print("Best seasonal ARIMA parameters:", stepwise_fit.seasonal_order)
        
        # Fit the model with best parameters
        self.model = ARIMA(
            self.sales_ts, 
            order=stepwise_fit.order,
            seasonal_order=stepwise_fit.seasonal_order
        )
        
        self.fitted_model = self.model.fit()
        print("\nModel Summary:")
        print(self.fitted_model.summary())
    
    def forecast_sales(self, periods=12):
        """Generate and plot sales forecast."""
        self.forecast_periods = periods
        
        # Generate forecast
        forecast = self.fitted_model.get_forecast(steps=periods)
        forecast_mean = forecast.predicted_mean
        confidence_intervals = forecast.conf_int()
        
        # Plot the results
        plt.figure(figsize=(14, 6))
        
        # Plot historical data
        plt.plot(self.sales_ts.index, self.sales_ts, label='Historical Sales')
        
        # Plot forecast
        forecast_index = pd.date_range(
            start=self.sales_ts.index[-1] + pd.Timedelta(days=1), 
            periods=periods
        )
        
        plt.plot(forecast_index, forecast_mean, 'r--', label='Forecast')
        plt.fill_between(
            forecast_index,
            confidence_intervals.iloc[:, 0],
            confidence_intervals.iloc[:, 1],
            color='pink', alpha=0.3, label='95% Confidence Interval'
        )
        
        plt.title(f'Sales Forecast for Next {periods} Periods')
        plt.xlabel('Date')
        plt.ylabel('Sales')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('sales_forecast.png')
        plt.close()
        
        # Return forecast data
        forecast_df = pd.DataFrame({
            'Date': forecast_index,
            'Forecast': forecast_mean,
            'Lower_CI': confidence_intervals.iloc[:, 0],
            'Upper_CI': confidence_intervals.iloc[:, 1]
        })
        
        return forecast_df
    
    def generate_report(self):
        """Generate a complete analysis report with all visualizations."""
        print("\n" + "="*50)
        print("HISTORICAL SALES ANALYSIS REPORT")
        print("="*50)
        
        # Basic information
        print(f"\nAnalysis Period: {self.sales_ts.index[0].date()} to {self.sales_ts.index[-1].date()}")
        print(f"Total Sales: {self.sales_ts.sum():,.2f}")
        print(f"Average Daily Sales: {self.sales_ts.mean():,.2f}")
        
        # Generate all visualizations
        print("\nGenerating visualizations...")
        self.plot_sales_trend()
        self.plot_moving_averages()
        self.seasonal_decomposition()
        self.test_stationarity()
        self.plot_acf_pacf()
        
        # Build and evaluate model
        print("\nBuilding forecasting model...")
        self.build_arima_model()
        
        # Generate forecast
        print("\nGenerating forecast...")
        forecast = self.forecast_sales()
        
        print("\n" + "="*50)
        print("FORECAST SUMMARY")
        print("="*50)
        print(f"\nForecast Period: {forecast['Date'].iloc[0].date()} to {forecast['Date'].iloc[-1].date()}")
        print(f"Total Forecasted Sales: {forecast['Forecast'].sum():,.2f}")
        print(f"Average Daily Forecast: {forecast['Forecast'].mean():,.2f}")
        
        print("\nAnalysis complete! Check the generated image files for visualizations.")

# Example usage
if __name__ == "__main__":
    # Example file path - replace with your actual file path
    file_path = "sample_sales_data.csv"
    
    # Initialize analyzer
    analyzer = HistoricalSalesAnalyzer(file_path)
    
    # Load and analyze data
    if analyzer.load_data():
        analyzer.generate_report()
    else:
        print("Failed to load data. Please check the file path and format.")
