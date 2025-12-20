import { useParams } from 'react-router-dom';
import Navigation from '../../components/Navigation';
import './HACCP.css';

function MobileCompletion() {
  const { instanceId } = useParams();

  return (
    <div className="haccp-page">
      <Navigation />
      <div className="mobile-completion">
        <div className="completion-header">
          <h1>Complete Checklist</h1>
          <div className="progress">Check 1 of 3</div>
        </div>

        <div className="completion-content">
          <p className="coming-soon">Mobile completion interface coming soon...</p>
          <p>Instance ID: {instanceId}</p>
        </div>
      </div>
    </div>
  );
}

export default MobileCompletion;
