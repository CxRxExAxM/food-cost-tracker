import TextRenderer from './renderers/TextRenderer';
import TableRenderer from './renderers/TableRenderer';
import ChartRenderer from './renderers/ChartRenderer';
import './MessageBubble.css';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  const renderContent = () => {
    if (isUser) {
      return <div className="message-text">{message.content}</div>;
    }

    // Assistant message with potential rendering
    const renderType = message.result_type || 'text';

    switch (renderType) {
      case 'table':
        return (
          <>
            <TextRenderer content={message.content} />
            {message.result_data && <TableRenderer data={message.result_data} />}
          </>
        );
      case 'line_chart':
      case 'bar_chart':
      case 'comparison_bar':
      case 'variance_chart':
        return (
          <>
            <TextRenderer content={message.content} />
            {message.result_data && (
              <ChartRenderer type={renderType} data={message.result_data} />
            )}
          </>
        );
      default:
        return <TextRenderer content={message.content} />;
    }
  };

  return (
    <div className={`message-bubble ${isUser ? 'message-user' : 'message-assistant'}`}>
      {renderContent()}
    </div>
  );
}
