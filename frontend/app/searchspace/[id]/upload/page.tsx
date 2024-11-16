'use client';

import { useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useRouter } from 'next/navigation';
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";

interface FileStatus {
  filename: string;
  status: 'pending' | 'processing' | 'success' | 'error';
  message?: string;
  progress?: number;
}

export default function UploadPage({ params }: { params: { id: string } }) {
  const [files, setFiles] = useState<File[]>([]);
  const [fileStatuses, setFileStatuses] = useState<FileStatus[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Utilizzare una URL configurabile
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/user/upload/${params.id}/${token}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connesso');
      setIsConnected(true);
    };

    // Gestione strutturata dei messaggi
    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (error) {
        console.error('Errore nel parsing del messaggio:', error);
      }
    };

    // Gestione degli errori migliorata
    websocket.onerror = (error) => {
      console.error('Errore WebSocket:', error);
      setIsConnected(false);
      // Notifica all'utente
    };

    setWs(websocket);

    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, [params.id, router]);

  const { getRootProps, getInputProps } = useDropzone({
    onDrop: async (acceptedFiles) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not connected');
        return;
      }

      setFiles(acceptedFiles);
      
      // Initialize file statuses
      const initialStatuses: FileStatus[] = acceptedFiles.map(file => ({
        filename: file.name,
        status: 'pending',
        progress: 0
      }));
      setFileStatuses(initialStatuses);

      // Process each file
      for (const file of acceptedFiles) {
        try {
          const reader = new FileReader();
          reader.onload = async () => {
            if (reader.result) {
              // Update status to processing
              setFileStatuses(prev => prev.map(status => 
                status.filename === file.name 
                  ? { ...status, status: 'processing', progress: 20 }
                  : status
              ));

              // Send file through WebSocket
              ws.send(JSON.stringify({
                type: 'bytes',
                bytes: reader.result,
                form: {
                  filename: file.name,
                  content_type: file.type
                }
              }));
            }
          };
          reader.readAsArrayBuffer(file);
        } catch (error) {
          console.error(`Error processing file ${file.name}:`, error);
          setFileStatuses(prev => prev.map(status => 
            status.filename === file.name 
              ? { ...status, status: 'error', message: 'Error reading file' }
              : status
          ));
        }
      }
    }
  });

  const handleWebSocketMessage = (data: any) => {
    setFileStatuses(prevStatuses => {
      const newStatuses = [...prevStatuses];
      const fileIndex = newStatuses.findIndex(f => f.filename === data.filename);
      
      if (fileIndex >= 0) {
        newStatuses[fileIndex] = {
          ...newStatuses[fileIndex],
          status: getFileStatus(data.type),
          message: data.message,
          progress: calculateProgress(data)
        };
      }
      
      return newStatuses;
    });
  };

  const getFileStatus = (type: string): FileStatus['status'] => {
    switch (type) {
      case 'error': return 'error';
      case 'success': return 'success';
      default: return 'processing';
    }
  };

  const calculateProgress = (data: any): number => {
    if (data.type === 'success') return 100;
    if (data.type === 'error') return 0;
    return data.progress || 0;
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Upload Files</h1>
      
      <div {...getRootProps()} className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors">
        <input {...getInputProps()} />
        <p>Drag and drop files here, or click to select files</p>
      </div>

      <div className="mt-8 space-y-4">
        {fileStatuses.map((fileStatus, index) => (
          <div key={index} className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">{fileStatus.filename}</span>
              {fileStatus.status === 'success' && (
                <CheckCircle2 className="text-green-500" />
              )}
              {fileStatus.status === 'error' && (
                <AlertCircle className="text-red-500" />
              )}
              {fileStatus.status === 'processing' && (
                <Info className="text-blue-500 animate-pulse" />
              )}
            </div>
            
            <Progress value={fileStatus.progress || 0} className="mb-2" />
            
            {fileStatus.message && (
              <Alert variant={fileStatus.status === 'error' ? 'destructive' : 'default'}>
                <AlertTitle>
                  {fileStatus.status === 'error' ? 'Error' : 'Status'}
                </AlertTitle>
                <AlertDescription>
                  {fileStatus.message}
                </AlertDescription>
              </Alert>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
