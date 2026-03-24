import './TextRenderer.css';

export default function TextRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="text-renderer">
      {content}
    </div>
  );
}
