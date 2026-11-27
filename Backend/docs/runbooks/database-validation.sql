-- Database validation for docs/DATABASE.md.
-- Run after the document SQL blocks and the auth/storage stubs.
\set ON_ERROR_STOP on

\echo '## admin fixture'
insert into auth.users (id, email, last_sign_in_at)
values ('00000000-0000-0000-0000-0000000000a1', 'admin@test', now());
insert into staff (user_id, email, display_name, role)
values ('00000000-0000-0000-0000-0000000000a1', 'admin@test', 'Admin', 'admin');

\echo '## page, sections, unpublish, republish'
do $$
declare
  v_admin uuid := '00000000-0000-0000-0000-0000000000a1';
  v_group uuid; v_proj uuid; v_page uuid; v_sec uuid; v_ver uuid;
  v_groups uuid[] := '{}';
  v_projs uuid[] := '{}';
  v_secs uuid[] := '{}';
  v_secvers uuid[] := '{}';
  v_keys page_section_key[] := array['hero','proof','services','not-sure','work','process','about','testimonials','faqs','contact']::page_section_key[];
  i int; n int; n_reval int; v_tags text[];
begin
  for i in 1..3 loop
    insert into content_item (kind, created_by) values ('service_group', v_admin) returning id into v_group;
    v_ver := create_draft(v_group, v_admin);
    update service_group_version set title = 'Group ' || i where version_id = v_ver;
    perform publish_content(v_group, v_ver, v_admin);
    v_groups := v_groups || v_group;
  end loop;

  for i in 1..3 loop
    insert into content_item (kind, slug, created_by) values ('project', 'proj-' || i, v_admin) returning id into v_proj;
    v_ver := create_draft(v_proj, v_admin);
    update project_version
      set title = 'Project ' || i, client = 'Client', client_need = 'Need',
          built = 'Built', result = 'Result', category = 'Category', sort_order = i
      where version_id = v_ver;
    insert into approval (version_id, subject_kind, scopes, approved_by_name, approved_on, recorded_by)
    values (v_ver, 'project', array['result']::approval_scope[], 'Client',
            (now() at time zone 'Europe/London')::date, v_admin);
    perform publish_content(v_proj, v_ver, v_admin);
    v_projs := v_projs || v_proj;
  end loop;

  insert into content_item (kind, path, created_by) values ('landing_page', '/', v_admin) returning id into v_page;

  for i in 1..10 loop
    insert into content_item (kind, created_by) values ('page_section', v_admin) returning id into v_sec;
    v_secs := v_secs || v_sec;
    insert into page_section (item_id, page_id, section_key, sort_order) values (v_sec, v_page, v_keys[i], i);
    v_ver := create_draft(v_sec, v_admin);
    v_secvers := v_secvers || v_ver;
    if v_keys[i] = 'services' then
      insert into section_version_item (version_id, item_id, item_kind, sort_order)
      select v_ver, g, 'service_group', row_number() over () from unnest(v_groups) g;
    elsif v_keys[i] = 'work' then
      insert into section_version_item (version_id, item_id, item_kind, sort_order)
      select v_ver, p, 'project', null from unnest(v_projs) p;
    elsif v_keys[i] = 'about' then
      insert into section_paragraph (version_id, sort_order, text) values (v_ver, 0, 'About paragraph.');
    end if;
  end loop;

  v_ver := create_draft(v_page, v_admin);
  update content_seo set seo_title = 'Leafclutch', seo_description = 'Build and support for UK teams.' where version_id = v_ver;
  perform publish_page(v_page, v_ver, v_secvers, v_admin);

  select count(*) into n from content_publication where item_id = v_page or item_id = any(v_secs);
  if n <> 11 then raise exception 'fixture: expected 11 live pointers, got %', n; end if;
  raise notice 'PASS fixture: page and ten sections published';

  select count(*) into n_reval from revalidation;
  perform unpublish_content(v_page, v_admin);

  select count(*) into n from revalidation;
  if n <> n_reval + 1 then raise exception 'unpublish: % revalidation rows, expected %', n, n_reval + 1; end if;
  select tags into v_tags from revalidation order by id desc limit 1;
  if (select array_agg(t order by t) from unnest(v_tags) t)
     is distinct from
     (select array_agg(t order by t) from unnest(array['page:/', 'routes']) t) then
    raise exception 'unpublish: newest revalidation tags %, expected exactly {page:/,routes}', v_tags;
  end if;

  select count(*) into n from content_publication where item_id = v_page or item_id = any(v_secs);
  if n <> 0 then raise exception 'unpublish: % pointers remain', n; end if;

  select count(*) into n from content_version where item_id = v_page and status = 'draft';
  if n <> 1 then raise exception 'unpublish: page drafts %', n; end if;

  select count(*) into n from content_version where item_id = any(v_secs) and status = 'draft';
  if n <> 10 then raise exception 'unpublish: section drafts %', n; end if;

  raise notice 'PASS unpublish landing page: 11 pointers removed, 11 drafts exist';

  select array_agg(cv.id) into v_secvers from content_version cv where cv.item_id = any(v_secs) and cv.status = 'draft';
  select cv.id into v_ver from content_version cv where cv.item_id = v_page and cv.status = 'draft';

  perform publish_page(v_page, v_ver, v_secvers, v_admin);

  select count(*) into n from content_publication where item_id = v_page or item_id = any(v_secs);
  if n <> 11 then raise exception 'republish: % pointers', n; end if;

  raise notice 'PASS publish_page republished the page from the 11 drafts';
end;
$$;

\echo '## service lifecycle'
do $$
declare
  v_admin uuid := '00000000-0000-0000-0000-0000000000a1';
  v_group uuid; v_serv uuid; v_ver uuid; v_draft uuid; n int;
  n_reval int; v_tags text[];
begin
  select id into v_group from content_item where kind = 'service_group' order by created_at limit 1;

  insert into content_item (kind, slug, created_by) values ('service', 'svc-a', v_admin) returning id into v_serv;
  v_ver := create_draft(v_serv, v_admin);
  update service_version
    set group_item_id = v_group, title = 'Service A', summary = 'Summary',
        long_description = 'Long description', sort_order = 0
    where version_id = v_ver;
  perform publish_content(v_serv, v_ver, v_admin);
  select count(*) into n from content_publication where item_id = v_serv;
  if n <> 1 then raise exception 'publish: % pointers', n; end if;

  perform unpublish_content(v_serv, v_admin);
  select count(*) into n from content_publication where item_id = v_serv;
  if n <> 0 then raise exception 'unpublish: % pointers', n; end if;
  select count(*) into n from content_version where item_id = v_serv and status = 'draft';
  if n <> 1 then raise exception 'unpublish: % open drafts', n; end if;
  select count(*) into n from content_version where item_id = v_serv;
  if n <> 2 then raise exception 'unpublish: % versions', n; end if;
  select count(*) into n from content_version where item_id = v_serv and status = 'published';
  if n <> 1 then raise exception 'unpublish: % published versions kept', n; end if;
  select count(*) into n from audit_log where action = 'unpublish' and entity_id = v_serv::text;
  if n <> 1 then raise exception 'unpublish: % audit rows', n; end if;
  raise notice 'PASS unpublish service: pointer gone, one draft, published version kept, audit written';

  perform unpublish_content(v_serv, v_admin);
  select count(*) into n from content_version where item_id = v_serv;
  if n <> 2 then raise exception 'second unpublish: % versions', n; end if;
  select count(*) into n from audit_log where action = 'unpublish' and entity_id = v_serv::text;
  if n <> 2 then raise exception 'second unpublish: % audit rows', n; end if;
  raise notice 'PASS second unpublish: no new draft, audit row still written (documented)';

  select id into v_draft from content_version where item_id = v_serv and status = 'draft';
  perform publish_content(v_serv, v_draft, v_admin);
  v_draft := create_draft(v_serv, v_admin);
  select count(*) into n from content_version where item_id = v_serv;
  if n <> 3 then raise exception 'edit draft: % versions', n; end if;
  perform unpublish_content(v_serv, v_admin);
  select count(*) into n from content_version where item_id = v_serv;
  if n <> 3 then raise exception 'unpublish with open draft: % versions', n; end if;
  select count(*) into n from content_publication where item_id = v_serv;
  if n <> 0 then raise exception 'unpublish with open draft: % pointers', n; end if;
  select count(*) into n from audit_log where action = 'unpublish' and entity_id = v_serv::text;
  if n <> 3 then raise exception 'unpublish with open draft: % audit rows', n; end if;
  select count(*) into n from content_version where item_id = v_serv and status = 'draft' and id = v_draft;
  if n <> 1 then raise exception 'unpublish did not reuse the open draft'; end if;
  raise notice 'PASS unpublish reuses an existing open draft: pointer gone, third audit row';

  perform publish_content(v_serv, v_draft, v_admin);
  select count(*) into n_reval from revalidation;
  perform archive_content(v_serv, v_admin);
  select count(*) into n from content_publication where item_id = v_serv;
  if n <> 0 then raise exception 'archive: % pointers', n; end if;
  select count(*) into n from content_version where item_id = v_serv and status in ('draft', 'in_review');
  if n <> 0 then raise exception 'archive created % drafts', n; end if;
  select count(*) into n from content_item where id = v_serv and archived_at is not null;
  if n <> 1 then raise exception 'archive: not archived'; end if;
  select count(*) into n from content_item where id = v_serv and archived_by is not null;
  if n <> 1 then raise exception 'archive: archived_by not set'; end if;
  select count(*) into n from audit_log where action = 'archive' and entity_id = v_serv::text;
  if n <> 1 then raise exception 'archive: % audit rows', n; end if;
  select count(*) into n from revalidation;
  if n <> n_reval + 1 then raise exception 'archive: % revalidation rows, expected %', n, n_reval + 1; end if;
  select tags into v_tags from revalidation order by id desc limit 1;
  if (select array_agg(t order by t) from unnest(v_tags) t)
     is distinct from
     (select array_agg(t order by t) from unnest(array['page:/']) t) then
    raise exception 'archive: newest revalidation tags %, expected exactly {page:/}', v_tags;
  end if;
  raise notice 'PASS archive: no draft, archived flag, audit row, one page:/ cache tag';

  select count(*) into n_reval from revalidation;
  perform restore_content(v_serv, v_admin);
  select count(*) into n from content_item where id = v_serv and archived_at is null and archived_by is null;
  if n <> 1 then raise exception 'restore: flags not cleared'; end if;
  select count(*) into n from content_version where item_id = v_serv and status in ('draft', 'in_review');
  if n <> 0 then raise exception 'restore created % drafts', n; end if;
  select count(*) into n from content_publication where item_id = v_serv;
  if n <> 0 then raise exception 'restore: pointer exists'; end if;
  select count(*) into n from revalidation;
  if n <> n_reval then raise exception 'restore: % revalidation rows, expected %', n, n_reval; end if;
  raise notice 'PASS restore: flags cleared, unpublished, no draft, no pointer, no cache tag';
end;
$$;

\echo '## delete and refusals'
do $$
declare
  v_admin uuid := '00000000-0000-0000-0000-0000000000a1';
  v_group uuid; v_serv uuid; v_ver uuid; v_proj uuid; v_legal uuid; v_sec uuid; v_secver uuid;
  v_fixed uuid; v_fixed_sec uuid; v_settings uuid; n int; n_reval int; v_refused boolean;
begin
  select id into v_group from content_item where kind = 'service_group' order by created_at limit 1;

  insert into content_item (kind, slug, created_by) values ('service', 'svc-delete', v_admin) returning id into v_serv;
  v_ver := create_draft(v_serv, v_admin);
  update service_version set group_item_id = v_group, title = 'Delete Me', summary = 'S',
    long_description = 'L', sort_order = 0 where version_id = v_ver;

  select count(*) into n_reval from revalidation;
  perform delete_content(v_serv, v_admin);
  if exists (select 1 from content_item where id = v_serv) then raise exception 'delete left the item'; end if;
  if exists (select 1 from content_version where item_id = v_serv) then raise exception 'delete left versions'; end if;
  select count(*) into n from audit_log where action = 'delete' and entity_id = v_serv::text;
  if n <> 1 then raise exception 'delete audit rows %', n; end if;
  select count(*) into n from revalidation;
  if n <> n_reval then raise exception 'delete: % revalidation rows, expected %', n, n_reval; end if;
  raise notice 'PASS delete never-published service: row and versions gone, one audit row, no cache tag';

  insert into content_item (kind, path, created_by) values ('legal_page', '/terms-test', v_admin) returning id into v_legal;
  perform create_draft(v_legal, v_admin);
  perform delete_content(v_legal, v_admin);
  insert into content_item (kind, path, created_by) values ('legal_page', '/terms-test', v_admin) returning id into v_legal;
  perform create_draft(v_legal, v_admin);
  perform delete_content(v_legal, v_admin);
  if exists (select 1 from content_item where id = v_legal) then raise exception 'second legal delete left the item'; end if;
  if exists (select 1 from content_version where item_id = v_legal) then raise exception 'second legal delete left versions'; end if;
  raise notice 'PASS legal page draft deleted twice and its path reused';

  select id into v_serv from content_item where kind = 'service' and slug = 'svc-a';
  v_refused := false;
  begin
    perform delete_content(v_serv, v_admin);
  exception when others then
    v_refused := true;
    if sqlerrm not like '%has been published%' then raise; end if;
  end;
  if not v_refused then raise exception 'delete published was allowed'; end if;
  select count(*) into n from content_item where id = v_serv;
  if n <> 1 then raise exception 'published refusal removed the item'; end if;
  raise notice 'PASS delete refuses a published item';

  select id into v_fixed from content_item where kind = 'landing_page' and path = '/';
  v_refused := false;
  begin
    perform delete_content(v_fixed, v_admin);
  exception when others then
    v_refused := true;
    if sqlerrm not like '%fixed item%' then raise; end if;
  end;
  if not v_refused then raise exception 'delete fixed landing page was allowed'; end if;
  select count(*) into n from content_item where id = v_fixed;
  if n <> 1 then raise exception 'fixed refusal removed the landing page'; end if;

  select item_id into v_fixed_sec from page_section where section_key = 'hero';
  v_refused := false;
  begin
    perform delete_content(v_fixed_sec, v_admin);
  exception when others then
    v_refused := true;
    if sqlerrm not like '%fixed item%' then raise; end if;
  end;
  if not v_refused then raise exception 'delete fixed page_section was allowed'; end if;
  select count(*) into n from content_item where id = v_fixed_sec;
  if n <> 1 then raise exception 'fixed refusal removed the section item'; end if;

  insert into content_item (kind, created_by) values ('settings', v_admin) returning id into v_settings;
  v_refused := false;
  begin
    perform delete_content(v_settings, v_admin);
  exception when others then
    v_refused := true;
    if sqlerrm not like '%fixed item%' then raise; end if;
  end;
  if not v_refused then raise exception 'delete settings was allowed'; end if;
  select count(*) into n from content_item where id = v_settings;
  if n <> 1 then raise exception 'fixed refusal removed the settings item'; end if;
  raise notice 'PASS delete refuses the fixed kinds: landing page, section, settings';

  insert into content_item (kind, slug, created_by) values ('project', 'proj-del', v_admin) returning id into v_proj;
  v_ver := create_draft(v_proj, v_admin);
  insert into approval (version_id, subject_kind, scopes, approved_by_name, approved_on, recorded_by)
  values (v_ver, 'project', array['result']::approval_scope[], 'Client',
          (now() at time zone 'Europe/London')::date, v_admin);
  v_refused := false;
  begin
    perform delete_content(v_proj, v_admin);
  exception when others then
    v_refused := true;
    if sqlerrm not like '%approval evidence%' then raise; end if;
  end;
  if not v_refused then raise exception 'delete approved was allowed'; end if;
  select count(*) into n from content_item where id = v_proj;
  if n <> 1 then raise exception 'approval refusal removed the item'; end if;
  raise notice 'PASS delete refuses an approved item';

  insert into content_item (kind, slug, created_by) values ('project', 'proj-ref', v_admin) returning id into v_proj;
  perform create_draft(v_proj, v_admin);
  select item_id into v_sec from page_section where section_key = 'work';
  v_secver := create_draft(v_sec, v_admin);
  insert into section_version_item (version_id, item_id, item_kind, sort_order)
  values (v_secver, v_proj, 'project', null);
  v_refused := false;
  begin
    perform delete_content(v_proj, v_admin);
  exception when others then
    v_refused := true;
    if sqlerrm not like '%referenced by a section version%' then raise; end if;
  end;
  if not v_refused then raise exception 'delete referenced was allowed'; end if;
  select count(*) into n from content_item where id = v_proj;
  if n <> 1 then raise exception 'section reference refusal removed the item'; end if;
  raise notice 'PASS delete refuses an item referenced by a section version';

  insert into content_item (kind, created_by) values ('service_group', v_admin) returning id into v_group;
  perform create_draft(v_group, v_admin);
  insert into content_item (kind, slug, created_by) values ('service', 'svc-group', v_admin) returning id into v_serv;
  v_ver := create_draft(v_serv, v_admin);
  update service_version set group_item_id = v_group, title = 'Service B', summary = 'S',
    long_description = 'L', sort_order = 0 where version_id = v_ver;
  v_refused := false;
  begin
    perform delete_content(v_group, v_admin);
  exception when others then
    v_refused := true;
    if sqlerrm not like '%referenced by a service%' then raise; end if;
  end;
  if not v_refused then raise exception 'delete group with service was allowed'; end if;
  select count(*) into n from content_item where id = v_group;
  if n <> 1 then raise exception 'group refusal removed the item'; end if;
  select count(*) into n from service_version where group_item_id = v_group;
  if n <> 1 then raise exception 'group refusal removed its service_version row'; end if;
  raise notice 'PASS delete refuses a group with a service version';
end;
$$;

\echo '## archive and restore the page'
do $$
declare
  v_admin uuid := '00000000-0000-0000-0000-0000000000a1';
  v_page uuid; v_ids uuid[]; n_before int; n_after int; n_restore int; n int;
  n_reval int; v_tags text[];
begin
  select id into v_page from content_item where kind = 'landing_page' and path = '/';
  select array_agg(item_id) into v_ids from page_section where page_id = v_page;
  v_ids := v_ids || v_page;

  select count(*) into n_before from content_version
  where item_id = any(v_ids) and status in ('draft', 'in_review');

  select count(*) into n_reval from revalidation;
  perform archive_content(v_page, v_admin);

  select count(*) into n_after from content_version
  where item_id = any(v_ids) and status in ('draft', 'in_review');
  if n_after <> n_before then
    raise exception 'archive created drafts: % -> %', n_before, n_after;
  end if;

  select count(*) into n from content_item where id = any(v_ids) and archived_at is not null;
  if n <> 11 then raise exception 'archive: % of 11 archived', n; end if;

  select count(*) into n from content_item where id = any(v_ids) and archived_by is not null;
  if n <> 11 then raise exception 'archive: % of 11 have archived_by', n; end if;

  select count(*) into n from content_publication where item_id = any(v_ids);
  if n <> 0 then raise exception 'archive: % pointers remain', n; end if;

  select count(*) into n from audit_log where action = 'archive' and entity_id = v_page::text;
  if n <> 1 then raise exception 'archive audit rows %', n; end if;

  select count(*) into n from revalidation;
  if n <> n_reval + 1 then raise exception 'archive: % revalidation rows, expected %', n, n_reval + 1; end if;
  select tags into v_tags from revalidation order by id desc limit 1;
  if (select array_agg(t order by t) from unnest(v_tags) t)
     is distinct from
     (select array_agg(t order by t) from unnest(array['page:/', 'routes']) t) then
    raise exception 'archive: newest revalidation tags %, expected exactly {page:/,routes}', v_tags;
  end if;

  raise notice 'PASS archive page: 11 items archived, no drafts created, pointer gone, audit row, page:/ and routes cache tag';

  select count(*) into n_restore from content_version
  where item_id = any(v_ids) and status in ('draft', 'in_review');
  select count(*) into n_reval from revalidation;
  perform restore_content(v_page, v_admin);

  select count(*) into n from content_item where id = any(v_ids) and archived_at is null;
  if n <> 11 then raise exception 'restore: % of 11 cleared', n; end if;
  select count(*) into n from content_item where id = any(v_ids) and archived_by is null;
  if n <> 11 then raise exception 'restore: % of 11 have archived_by cleared', n; end if;
  select count(*) into n from content_publication where item_id = any(v_ids);
  if n <> 0 then raise exception 'restore: pointer exists'; end if;

  select count(*) into n from content_version
  where item_id = any(v_ids) and status in ('draft', 'in_review');
  if n <> n_restore then
    raise exception 'restore created drafts: % -> %', n_restore, n;
  end if;

  select count(*) into n from revalidation;
  if n <> n_reval then raise exception 'restore: % revalidation rows, expected %', n, n_reval; end if;

  raise notice 'PASS restore page: all 11 flags cleared, nothing live, no new draft, no cache tag';
end;
$$;

\echo '## archive page with a live section and no page pointer'
do $$
declare
  v_admin uuid := '00000000-0000-0000-0000-0000000000a1';
  v_page uuid; v_hero uuid; v_ver uuid; v_ids uuid[];
  n int; n_before int; n_after int; n_reval int; n_unpub int; n_unpub_page int;
  n_archive int; v_tags text[]; v_audit_entity text;
begin
  select id into v_page from content_item where kind = 'landing_page' and path = '/';
  select item_id into v_hero from page_section where page_id = v_page and section_key = 'hero';
  select array_agg(item_id) into v_ids from page_section where page_id = v_page;
  v_ids := v_ids || v_page;

  select count(*) into n from content_publication where item_id = any(v_ids);
  if n <> 0 then raise exception 'precondition: % pointers before publishing the hero', n; end if;

  v_ver := create_draft(v_hero, v_admin);
  perform publish_content(v_hero, v_ver, v_admin);

  select count(*) into n from content_publication where item_id = v_page;
  if n <> 0 then raise exception 'setup: page pointer present'; end if;
  select count(*) into n from content_publication where item_id = v_hero;
  if n <> 1 then raise exception 'setup: hero pointers %', n; end if;

  select count(*) into n_before from content_version
  where item_id = any(v_ids) and status in ('draft', 'in_review');
  select count(*) into n_reval from revalidation;
  select count(*) into n_unpub from audit_log where action = 'unpublish';
  select count(*) into n_unpub_page from audit_log
  where action = 'unpublish' and entity_kind = 'landing_page' and entity_id = v_page::text;
  select count(*) into n_archive from audit_log where action = 'archive';

  perform archive_content(v_page, v_admin);

  select count(*) into n from content_item where id = any(v_ids) and archived_at is not null;
  if n <> 11 then raise exception 'archive page with live section: % of 11 archived', n; end if;

  select count(*) into n from content_publication where item_id = any(v_ids);
  if n <> 0 then raise exception 'archive page with live section: % pointers remain', n; end if;

  select count(*) into n from audit_log where action = 'unpublish';
  if n <> n_unpub + 1 then
    raise exception 'archive page with live section: % unpublish rows, expected %', n, n_unpub + 1;
  end if;
  select count(*) into n from audit_log
  where action = 'unpublish' and entity_kind = 'landing_page' and entity_id = v_page::text;
  if n <> n_unpub_page + 1 then
    raise exception 'archive page with live section: % page unpublish rows, expected %', n, n_unpub_page + 1;
  end if;
  select entity_id into v_audit_entity from audit_log where action = 'unpublish' order by id desc limit 1;
  if v_audit_entity is distinct from v_page::text then
    raise exception 'archive page with live section: newest unpublish row names %', v_audit_entity;
  end if;

  select count(*) into n from audit_log where action = 'archive';
  if n <> n_archive + 1 then
    raise exception 'archive page with live section: % archive rows, expected %', n, n_archive + 1;
  end if;
  select entity_id into v_audit_entity from audit_log where action = 'archive' order by id desc limit 1;
  if v_audit_entity is distinct from v_page::text then
    raise exception 'archive page with live section: newest archive row names %', v_audit_entity;
  end if;

  select count(*) into n from revalidation;
  if n <> n_reval + 1 then
    raise exception 'archive page with live section: % revalidation rows, expected %', n, n_reval + 1;
  end if;
  select tags into v_tags from revalidation order by id desc limit 1;
  if (select array_agg(t order by t) from unnest(v_tags) t)
     is distinct from
     (select array_agg(t order by t) from unnest(array['page:/', 'routes']) t) then
    raise exception 'archive page with live section: newest revalidation tags %, expected exactly {page:/,routes}', v_tags;
  end if;

  select count(*) into n_after from content_version
  where item_id = any(v_ids) and status in ('draft', 'in_review');
  if n_after <> n_before then
    raise exception 'archive page with live section: drafts % -> %', n_before, n_after;
  end if;

  raise notice 'PASS archive page with a live section and no page pointer: 11 archived, pointers gone, one page unpublish audit row, page:/ and routes cache tag, no new draft';

  perform restore_content(v_page, v_admin);

  select count(*) into n from content_item where id = any(v_ids) and archived_at is null;
  if n <> 11 then raise exception 'restore page: % of 11 cleared', n; end if;
  select count(*) into n from content_item where id = any(v_ids) and archived_by is null;
  if n <> 11 then raise exception 'restore page: % of 11 have archived_by cleared', n; end if;
end;
$$;
