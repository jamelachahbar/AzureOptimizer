import React, { useState, useEffect, useRef } from 'react';
import { Typography, useTheme } from '@mui/material';

interface TypewriterEffectSmoothProps {
  words: Array<{ text: string; className?: string }>;
  speed?: number;
  cursorBlinkSpeed?: number;
  variant?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

const TypewriterEffectSmooth: React.FC<TypewriterEffectSmoothProps> = ({
  words,
  speed = 100,
  cursorBlinkSpeed = 500,
  variant = 'h5',
}) => {
  const [isTypingDone, setIsTypingDone] = useState(false);
  const [showCursor, setShowCursor] = useState(true);
  const theme = useTheme();
  
  // Use useRef to persist text across re-renders
  const displayedTextRef = useRef('');
  const wordIndexRef = useRef(0);
  const charIndexRef = useRef(0);
  const [, setDisplayedText] = useState('');

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const type = () => {
      const currentWord = words[wordIndexRef.current].text;

      if (charIndexRef.current < currentWord.length) {
        displayedTextRef.current += currentWord[charIndexRef.current];
        setDisplayedText(displayedTextRef.current); // Trigger a re-render to update the displayed text
        charIndexRef.current += 1;
        timeoutId = setTimeout(type, speed);
      } else if (wordIndexRef.current < words.length - 1) {
        displayedTextRef.current += ' '; // Add space between words
        setDisplayedText(displayedTextRef.current); // Trigger a re-render to update the displayed text
        wordIndexRef.current += 1;
        charIndexRef.current = 0;
        timeoutId = setTimeout(type, speed);
      } else {
        setIsTypingDone(true);
      }
    };

    type();

    return () => clearTimeout(timeoutId);
  }, [words, speed]);

  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, cursorBlinkSpeed);

    return () => clearInterval(cursorInterval);
  }, [cursorBlinkSpeed]);

  const renderTextWithHighlight = () => {
    const lastWord = words[words.length - 1].text;
    const textBeforeLastWord = displayedTextRef.current.slice(0, displayedTextRef.current.length - lastWord.length);

    if (isTypingDone) {
      return (
        <>
          {textBeforeLastWord}
          <span style={{ color: theme.palette.primary.main }}>{lastWord}</span>
        </>
      );
    } else {
      return <>{displayedTextRef.current}</>;
    }
  };

  return (
    <Typography variant={variant} sx={{ mb: 4, textAlign: 'center', color: theme.palette.text.primary }}>
      {renderTextWithHighlight()}
      <span style={{ visibility: showCursor ? 'visible' : 'hidden' }}>|</span>
    </Typography>
  );
};

export default TypewriterEffectSmooth;
