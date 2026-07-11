
-- Create Policies for Community Applications
CREATE POLICY "Allow users to manage their own application" ON public.community_applications FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow users to manage their own systems" ON public.community_application_systems FOR ALL TO authenticated USING (EXISTS (SELECT 1 FROM public.community_applications a WHERE a.id = application_id AND a.user_id = auth.uid())) WITH CHECK (EXISTS (SELECT 1 FROM public.community_applications a WHERE a.id = application_id AND a.user_id = auth.uid()));

CREATE POLICY "Allow users to manage their own proofs" ON public.community_application_proofs FOR ALL TO authenticated USING (EXISTS (SELECT 1 FROM public.community_applications a WHERE a.id = application_id AND a.user_id = auth.uid())) WITH CHECK (EXISTS (SELECT 1 FROM public.community_applications a WHERE a.id = application_id AND a.user_id = auth.uid()));

CREATE POLICY "Allow users to read their own reviews" ON public.community_application_reviews FOR SELECT TO authenticated USING (EXISTS (SELECT 1 FROM public.community_applications a WHERE a.id = application_id AND a.user_id = auth.uid()));
