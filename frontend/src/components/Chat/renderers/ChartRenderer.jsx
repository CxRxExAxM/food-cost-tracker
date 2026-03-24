import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './ChartRenderer.css';

export default function ChartRenderer({ type, data }) {
  if (!data) return null;

  const chartConfig = {
    margin: { top: 10, right: 10, left: 0, bottom: 0 },
    style: { fontSize: '12px' }
  };

  const renderChart = () => {
    switch (type) {
      case 'line_chart':
        return (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.data || []} {...chartConfig}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
              <XAxis dataKey="name" stroke="var(--text-secondary)" />
              <YAxis stroke="var(--text-secondary)" />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-primary)'
                }}
              />
              <Legend />
              {data.lines?.map((line, index) => (
                <Line
                  key={index}
                  type="monotone"
                  dataKey={line.key}
                  stroke={line.color || 'var(--color-green)'}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case 'bar_chart':
      case 'comparison_bar':
        return (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.data || []} {...chartConfig}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
              <XAxis dataKey="name" stroke="var(--text-secondary)" />
              <YAxis stroke="var(--text-secondary)" />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-primary)'
                }}
              />
              <Legend />
              {data.bars?.map((bar, index) => (
                <Bar
                  key={index}
                  dataKey={bar.key}
                  fill={bar.color || 'var(--color-green)'}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );

      default:
        return <div className="chart-placeholder">Chart type not implemented</div>;
    }
  };

  return (
    <div className="chart-renderer">
      {renderChart()}
    </div>
  );
}
