function iml_report_progress(percent, message)
fid = fopen('iml_progress.txt','a');
fprintf(fid, '%.1f\t%s\n', percent, message);
fclose(fid);
end
