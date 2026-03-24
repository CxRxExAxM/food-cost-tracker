import ReactMarkdown from 'react-markdown';
import './TextRenderer.css';

export default function TextRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="text-renderer">
      <ReactMarkdown
        components={{
          // Customize rendering if needed
          h1: ({node, ...props}) => <h1 style={{ fontSize: '1.2em', marginTop: '0.5em', marginBottom: '0.3em' }} {...props} />,
          h2: ({node, ...props}) => <h2 style={{ fontSize: '1.1em', marginTop: '0.5em', marginBottom: '0.3em' }} {...props} />,
          h3: ({node, ...props}) => <h3 style={{ fontSize: '1.05em', marginTop: '0.4em', marginBottom: '0.2em' }} {...props} />,
          ul: ({node, ...props}) => <ul style={{ marginTop: '0.3em', marginBottom: '0.3em', paddingLeft: '1.5em' }} {...props} />,
          ol: ({node, ...props}) => <ol style={{ marginTop: '0.3em', marginBottom: '0.3em', paddingLeft: '1.5em' }} {...props} />,
          li: ({node, ...props}) => <li style={{ marginBottom: '0.2em' }} {...props} />,
          p: ({node, ...props}) => <p style={{ marginTop: '0.3em', marginBottom: '0.3em' }} {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
