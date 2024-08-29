import React, { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Typography, useTheme } from '@mui/material';

interface FlipTextProps {
  texts: string[];
  interval?: number;
  className?: string;
}

const FlipText: React.FC<FlipTextProps> = ({ texts, interval = 3000, className }) => {
  const [currentText, setCurrentText] = useState(texts[0]);
  const [isAnimating, setIsAnimating] = useState(false);
  const theme = useTheme();

  const startAnimation = useCallback(() => {
    const nextText = texts[(texts.indexOf(currentText) + 1) % texts.length];
    setCurrentText(nextText);
    setIsAnimating(true);
  }, [currentText, texts]);

  useEffect(() => {
    if (!isAnimating) {
      const timer = setTimeout(() => {
        startAnimation();
      }, interval);
      return () => clearTimeout(timer);
    }
  }, [isAnimating, interval, startAnimation]);

  return (
    <motion.div
      key={currentText}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -40, x: 40, scale: 2, position: "absolute" }}
      transition={{ type: "spring", stiffness: 100, damping: 10 }}
      className={className}
      onAnimationComplete={() => setIsAnimating(false)}
    >
      <Typography
        variant="h3"
        component="span"
        style={{
          fontWeight: "bold",
          color: theme.palette.text.primary, // Match theme color
        }}
      >
        {currentText}
      </Typography>
    </motion.div>
  );
};

export default FlipText;
