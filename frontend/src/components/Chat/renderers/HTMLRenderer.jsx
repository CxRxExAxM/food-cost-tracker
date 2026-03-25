import './HTMLRenderer.css';

export default function HTMLRenderer({ content }) {
  if (!content) return null;

  // Safe to use dangerouslySetInnerHTML since content comes from our controlled backend
  // The agent generates the HTML, not user input
  return (
    <div
      className="html-renderer"
      dangerouslySetInnerHTML={{ __html: content }}
    />
  );
}
