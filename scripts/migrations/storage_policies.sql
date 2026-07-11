
-- Create Storage Bucket (if it doesn't exist)
INSERT INTO storage.buckets (id, name, public) VALUES ('community-proofs', 'community-proofs', false) ON CONFLICT DO NOTHING;

-- Allow authenticated users to upload their proofs
CREATE POLICY "Allow authenticated users to upload proofs"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'community-proofs');

-- Allow authenticated users to read proofs
CREATE POLICY "Allow authenticated users to read proofs"
ON storage.objects FOR SELECT TO authenticated
USING (bucket_id = 'community-proofs');

-- Allow users to update their own proofs
CREATE POLICY "Allow users to update their own proofs"
ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'community-proofs' AND auth.uid() = owner);

-- Allow users to delete their own proofs
CREATE POLICY "Allow users to delete their own proofs"
ON storage.objects FOR DELETE TO authenticated
USING (bucket_id = 'community-proofs' AND auth.uid() = owner);
