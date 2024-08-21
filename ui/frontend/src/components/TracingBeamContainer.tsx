import React, { useEffect, useRef } from 'react';
import { useTheme } from '@mui/material/styles';
import './TracingBeam.css'; // Ensure this file is included

interface TracingBeamContainerProps {
  children: React.ReactNode;
}

const TracingBeamContainer: React.FC<TracingBeamContainerProps> = ({ children }) => {
  const beamRef = useRef<HTMLDivElement>(null);
  const theme = useTheme();

  const handleScroll = () => {
    const beam = beamRef.current;
    if (!beam) return;

    const rect = beam.getBoundingClientRect();
    const parentRect = beam.parentElement?.getBoundingClientRect();
    if (!parentRect) return;

    const startScroll = window.scrollY;
    const endScroll = startScroll + window.innerHeight;
    const sectionStart = parentRect.top + window.scrollY;
    const sectionEnd = sectionStart + parentRect.height;

    if (sectionStart < endScroll && sectionEnd > startScroll) {
      const beamHeight = Math.min(endScroll - sectionStart, sectionEnd - startScroll);
      beam.style.height = `${beamHeight}px`;
      beam.style.top = `${Math.max(0, startScroll - sectionStart)}px`;
      beam.classList.add('active');
    } else {
      beam.classList.remove('active');
    }
  };

  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="tracing-beam-container">
      <div
        ref={beamRef}
        className="tracing-beam-vertical"
        style={{
          background: `linear-gradient(to bottom, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`
        }}
      ></div>
      <div className="content-container">
        {children}
      </div>
    </div>
  );
};

export default TracingBeamContainer;
