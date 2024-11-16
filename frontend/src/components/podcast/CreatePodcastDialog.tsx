import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Slider,
  Typography,
} from '@mui/material';
import { PodcastCreate } from '@/types/podcast';

interface CreatePodcastDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (data: PodcastCreate) => void;
}

export const CreatePodcastDialog: React.FC<CreatePodcastDialogProps> = ({
  open,
  onClose,
  onCreate,
}) => {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [wordCount, setWordCount] = useState(500);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate({
      title,
      content,
      word_count: wordCount,
    });
    setTitle('');
    setContent('');
    setWordCount(500);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>Create New Podcast</DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2} mt={1}>
            <TextField
              label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
              fullWidth
              multiline
              rows={6}
            />
            <Box>
              <Typography gutterBottom>Word Count: {wordCount}</Typography>
              <Slider
                value={wordCount}
                onChange={(_, value) => setWordCount(value as number)}
                min={100}
                max={2000}
                step={50}
                marks={[
                  { value: 100, label: '100' },
                  { value: 500, label: '500' },
                  { value: 1000, label: '1000' },
                  { value: 2000, label: '2000' },
                ]}
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" color="primary">
            Create
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};
