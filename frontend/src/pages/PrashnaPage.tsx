import React from 'react';
import PrashnaForm from '../features/prashna/PrashnaForm';

const PrashnaPage: React.FC = () => {
  return (
    <div className="max-w-3xl mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6 text-gray-900 dark:text-gray-100">Ask a Prashna</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        Enter your question and details to generate a Prashna Kundli based on the current moment.
      </p>
      
      <PrashnaForm />
    </div>
  );
};

export default PrashnaPage;
