import React from 'react';
import { motion } from 'framer-motion';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import type { GridProps } from '@mui/material/Grid';

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
}

const prompts = [
  "What are the maintenance steps for an HVAC system?",
  "How do I troubleshoot a leaking pipe?",
  "What are the safety checks for electrical equipment?",
  "How often should I replace air filters?"
];

const SuggestedPrompts: React.FC<SuggestedPromptsProps> = ({ onSelect }) => {
  return (
    // Overall smooth fade-in on load
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <Box sx={{ maxWidth: '900px', margin: '0 auto', padding: '32px 16px' }}>
        <Grid container spacing={3} justifyContent="center">
          {prompts.map((prompt, index) => (
            <Grid {...({ item: true, xs: 12, md: 6 } as GridProps)} key={index}>
              {/* ✅ Button animation with hover and entrance transition */}
              <motion.div
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ scale: 1.02 }}
                transition={{
                  delay: index * 0.08,
                  duration: 0.4,
                  ease: 'easeOut',
                  type: 'tween',
                }}
              >
                <Button
                  variant="outlined"
                  onClick={() => onSelect(prompt)}
                  fullWidth
                  sx={{
                    textAlign: 'left',
                    border: '2px solid black',
                    backgroundColor: 'transparent',
                    color: 'black',
                    fontWeight: 'bold',
                    padding: '12px 16px',
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      backgroundColor: '#f5f5f5',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                      borderColor: '#333',
                    },
                  }}
                >
                  {prompt}
                </Button>
              </motion.div>
            </Grid>
          ))}
        </Grid>
      </Box>
    </motion.div>
  );
};

export default SuggestedPrompts;
