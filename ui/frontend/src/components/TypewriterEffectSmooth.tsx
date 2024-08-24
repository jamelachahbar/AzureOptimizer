import React, { useState, useEffect } from 'react';
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
  const [displayedText, setDisplayedText] = useState('');
  const [isTypingDone, setIsTypingDone] = useState(false);
  const [showCursor, setShowCursor] = useState(true);
  const theme = useTheme();

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    let wordIndex = 0;
    let charIndex = 0;
    let currentText = ''; // Local variable to store current text

    const type = () => {
      const currentWord = words[wordIndex].text;

      if (charIndex < currentWord.length) {
        currentText += currentWord[charIndex];
        setDisplayedText(currentText);
        charIndex += 1;
        timeoutId = setTimeout(type, speed);
      } else if (wordIndex < words.length - 1) {
        currentText += ' '; // Add space between words
        setDisplayedText(currentText);
        wordIndex += 1;
        charIndex = 0;
        timeoutId = setTimeout(type, speed);
      } else {
        setIsTypingDone(true);
        setDisplayedText(currentText); // Finish typing the last word
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
    if (isTypingDone) {
      const lastWord = words[words.length - 1].text;
      const textBeforeLastWord = displayedText.slice(0, displayedText.length - lastWord.length);
      return (
        <>
          {textBeforeLastWord}
          <span style={{ color: theme.palette.primary.main }}>{lastWord}</span>
        </>
      );
    }
    return <>{displayedText}</>;
  };

  return (
    <Typography variant={variant} sx={{ mb: 4, textAlign: 'center', color: theme.palette.text.primary }}>
      {renderTextWithHighlight()}
      {isTypingDone && <span style={{ visibility: showCursor ? 'visible' : 'hidden' }}>|</span>}
    </Typography>
  );
};

export default TypewriterEffectSmooth;
