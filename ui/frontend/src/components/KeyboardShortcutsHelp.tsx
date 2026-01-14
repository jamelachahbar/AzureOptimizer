import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import KeyboardIcon from '@mui/icons-material/Keyboard';
import CloseIcon from '@mui/icons-material/Close';
import { formatKeyCombo, KeyboardShortcut } from '../utils/useKeyboardShortcuts';

interface KeyboardShortcutsHelpProps {
  shortcuts: KeyboardShortcut[];
}

/**
 * KeyboardShortcutsHelp Component
 * 
 * Displays a help dialog showing all available keyboard shortcuts.
 * Can be triggered by clicking the keyboard icon or pressing '?'.
 */
const KeyboardShortcutsHelp: React.FC<KeyboardShortcutsHelpProps> = ({ shortcuts }) => {
  const [open, setOpen] = useState(false);

  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  // Filter shortcuts that have descriptions
  const displayableShortcuts = shortcuts.filter(s => s.description);

  return (
    <>
      <Tooltip title="Keyboard Shortcuts (Press ? for help)">
        <IconButton
          onClick={handleOpen}
          size="small"
          sx={{ ml: 1 }}
          aria-label="keyboard shortcuts"
        >
          <KeyboardIcon />
        </IconButton>
      </Tooltip>

      <Dialog
        open={open}
        onClose={handleClose}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: { borderRadius: 2 }
        }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <KeyboardIcon color="primary" />
            <Typography variant="h6">Keyboard Shortcuts</Typography>
          </Box>
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        
        <DialogContent dividers>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold', width: '40%' }}>Shortcut</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {displayableShortcuts.map((shortcut, index) => (
                  <TableRow 
                    key={index}
                    sx={{ 
                      opacity: shortcut.enabled === false ? 0.5 : 1,
                      '&:last-child td, &:last-child th': { border: 0 }
                    }}
                  >
                    <TableCell>
                      <KeyCombo combo={shortcut.key} />
                    </TableCell>
                    <TableCell>
                      {shortcut.description}
                      {shortcut.enabled === false && (
                        <Typography 
                          variant="caption" 
                          color="text.secondary"
                          sx={{ ml: 1 }}
                        >
                          (disabled)
                        </Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          
          <Typography 
            variant="caption" 
            color="text.secondary"
            sx={{ display: 'block', mt: 2, textAlign: 'center' }}
          >
            Shortcuts are disabled when typing in input fields
          </Typography>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleClose}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

/**
 * KeyCombo Component
 * 
 * Renders a formatted keyboard combination with styled key chips.
 */
const KeyCombo: React.FC<{ combo: string }> = ({ combo }) => {
  const parts = combo.split('+');
  
  return (
    <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
      {parts.map((part, index) => (
        <React.Fragment key={index}>
          <Chip
            label={part.toUpperCase()}
            size="small"
            sx={{
              fontFamily: 'monospace',
              fontWeight: 'bold',
              fontSize: '0.75rem',
              height: 24,
              minWidth: 28,
              borderRadius: 1,
              backgroundColor: 'action.selected',
            }}
          />
          {index < parts.length - 1 && (
            <Typography variant="caption" color="text.secondary">+</Typography>
          )}
        </React.Fragment>
      ))}
    </Box>
  );
};

export default KeyboardShortcutsHelp;
export { KeyCombo };
