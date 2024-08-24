import React, { useState } from "react";
import { motion, useTransform, useMotionValue, useSpring } from "framer-motion";
import { useTheme } from "@mui/material/styles";

interface AnimatedTooltipProps {
  title: string;
  children: React.ReactNode;
}

export const AnimatedTooltip: React.FC<AnimatedTooltipProps> = ({ title, children }) => {
  const theme = useTheme();
  const [isHovered, setIsHovered] = useState(false);
  const springConfig = { stiffness: 100, damping: 10 };
  const x = useMotionValue(0);
  const rotate = useSpring(useTransform(x, [-100, 100], [-15, 15]), springConfig);
  const translateX = useSpring(useTransform(x, [-100, 100], [-10, 10]), springConfig);

  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
    const halfWidth = event.currentTarget.offsetWidth / 2;
    x.set(event.nativeEvent.offsetX - halfWidth);
  };

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onMouseMove={handleMouseMove}
      style={{ display: "inline-block", position: "relative" }}
    >
      {isHovered && (
        <motion.div
          initial={{ opacity: 0, y: 10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          style={{
            translateX: translateX,
            rotate: rotate,
            whiteSpace: "nowrap",
            backgroundColor: theme.palette.background.paper,
            color: theme.palette.text.primary,
            boxShadow: theme.shadows[4],
            padding: '8px',
            borderRadius: '8px',
            position: 'absolute',
            zIndex: 50,
            transform: 'translateX(-50%)',
            left: '50%',
            top: '-40px', // Adjust as needed to position the tooltip above the element
          }}
        >
          <div style={{ fontWeight: 'bold' }}>{title}</div>
        </motion.div>
      )}
      {children}
    </div>
  );
};
