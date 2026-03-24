import './TableRenderer.css';

export default function TableRenderer({ data }) {
  if (!data || !data.columns || !data.rows) return null;

  return (
    <div className="table-renderer">
      <table className="chat-table">
        <thead>
          <tr>
            {data.columns.map((col, index) => (
              <th key={index}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
